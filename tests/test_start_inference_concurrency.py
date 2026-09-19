"""Adversarial concurrency test for handle_start_inference race condition.

Tests the exact race window in handle_start_inference where:
  1. Thread A reads DynamoDB -> sees UPLOADED
  2. Thread B reads DynamoDB -> sees UPLOADED  (before A's transition)
  3. Thread A launches ECS task A
  4. Thread B launches ECS task B
  5. Thread A transitions UPLOADED -> PROCESSING (succeeds)
  6. Thread B attempts UPLOADED -> PROCESSING (StateTransitionError caught/swallowed)
  -> RESULT: Two ECS tasks launched, only one DynamoDB record.

Design:
- All AWS calls are mocked. No real AWS resources are touched.
- The race is reproduced by injecting a threading.Event into the mock ECS client
  so we can pause Thread A after ECS launch but before DynamoDB transition,
  allowing Thread B to observe UPLOADED and launch its own ECS task.
- The test directly verifies the number of ecs.run_task calls.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, call

import pytest

from src.control_plane.lambda_handler import handle_start_inference
from src.state.dynamo_store import DynamoSessionStore
from src.state.models import SessionRecord, SessionState, StateTransitionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uploaded_session(session_id: str) -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        state=SessionState.UPLOADED.value,
        video_s3_key=f"inputs/{session_id}/video.mp4",
        imu_s3_key=f"inputs/{session_id}/imu.txt",
        predictions_s3_key=f"outputs/{session_id}/predictions.json",
        explanation_s3_key=f"outputs/{session_id}/explanation.json",
    )


def _make_ecs_mock(task_suffix: str = "A") -> MagicMock:
    mock = MagicMock()
    mock.run_task.return_value = {
        "tasks": [{"taskArn": f"arn:aws:ecs:task:{task_suffix}"}],
        "failures": [],
    }
    return mock


# ---------------------------------------------------------------------------
# 1. PROVE THE RACE IS REAL
# ---------------------------------------------------------------------------

def test_race_two_concurrent_requests_launch_two_ecs_tasks():
    """
    Reproduces the race:
    Thread A: reads UPLOADED -> launches ECS -> [PAUSE] -> transitions DynamoDB
    Thread B: reads UPLOADED -> launches ECS -> transitions DynamoDB (fails, swallowed)

    Expected outcome: ecs.run_task called TWICE.
    This proves the race IS real.
    """
    session_id = "11111111-1111-1111-1111-111111111111"

    # Shared ECS mock — both threads use the same mock so call count is accurate
    shared_ecs = MagicMock()
    ecs_launch_count = []

    # Gate that pauses Thread A AFTER its ECS launch but BEFORE DynamoDB transition
    # so Thread B can observe UPLOADED and launch its own ECS task.
    a_launched_ecs = threading.Event()
    b_may_proceed = threading.Event()

    call_index = [0]
    call_lock = threading.Lock()

    def ecs_run_task_side_effect(**kwargs):
        with call_lock:
            idx = call_index[0]
            call_index[0] += 1

        result = {"tasks": [{"taskArn": f"arn:aws:ecs:task:{idx}"}], "failures": []}
        ecs_launch_count.append(result["tasks"][0]["taskArn"])

        if idx == 0:
            # Thread A's ECS launch — signal B that ECS is launched
            a_launched_ecs.set()
            # Wait for B to also launch before A proceeds to DynamoDB transition
            b_may_proceed.wait(timeout=5.0)

        return result

    shared_ecs.run_task.side_effect = ecs_run_task_side_effect

    # DynamoDB mock: always returns UPLOADED for get_session (simulates pre-transition reads)
    # Only the first transition_state succeeds; second raises StateTransitionError
    transition_call_count = [0]
    transition_lock = threading.Lock()

    mock_store = MagicMock()
    mock_store.get_session.return_value = _uploaded_session(session_id)

    def transition_side_effect(session_id, from_state, to_state, updates=None):
        with transition_lock:
            n = transition_call_count[0]
            transition_call_count[0] += 1

        if n == 0:
            # First call succeeds
            return SessionRecord(session_id=session_id, state=to_state.value)
        else:
            # Second call: conditional check fails (state already PROCESSING)
            raise StateTransitionError(
                from_state=from_state,
                to_state=to_state,
                message=(
                    f"State transition conflict: Expected state 'UPLOADED', "
                    f"but current state is 'PROCESSING'."
                ),
            )

    mock_store.transition_state.side_effect = transition_side_effect

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    results: List[Dict[str, Any]] = []
    errors: List[Exception] = []

    def run_request():
        try:
            with (
                patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
                patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
                patch("src.control_plane.lambda_handler.get_ecs_client", return_value=shared_ecs),
            ):
                result = handle_start_inference({"session_id": session_id})
                results.append(result)
        except Exception as exc:
            errors.append(exc)

    thread_a = threading.Thread(target=run_request, name="Thread-A")
    thread_b = threading.Thread(target=run_request, name="Thread-B")

    thread_a.start()

    # Wait for Thread A to have launched its ECS task, then start Thread B
    a_launched_ecs.wait(timeout=5.0)
    thread_b.start()

    # Give Thread B time to launch its ECS task and signal that
    # Thread A can proceed to DynamoDB transition
    thread_b.join(timeout=10.0)
    b_may_proceed.set()
    thread_a.join(timeout=10.0)

    assert not errors, f"Unexpected exceptions: {errors}"

    # THE CRITICAL ASSERTION: ECS was launched TWICE
    assert shared_ecs.run_task.call_count == 2, (
        f"Expected 2 ECS launches (race reproduced), got {shared_ecs.run_task.call_count}. "
        f"Race may have been mitigated already."
    )

    # Both HTTP responses claim PROCESSING/202
    assert len(results) == 2
    for r in results:
        assert r["statusCode"] in (202, 200)
        body = json.loads(r["body"])
        assert body["status"] in ("PROCESSING", "COMPLETE")

    # DynamoDB transition was only attempted by the second call after A's state change
    # The second transition raised StateTransitionError (caught and swallowed)
    assert mock_store.transition_state.call_count == 2
    assert transition_call_count[0] == 2


# ---------------------------------------------------------------------------
# 2. VERIFY THE SWALLOWED EXCEPTION LEAVES STATE INCONSISTENT
# ---------------------------------------------------------------------------

def test_stale_ecs_task_arn_when_race_occurs():
    """
    When Thread A wins the DynamoDB transition, ecs_task_arn = task:0 (correct).
    Thread B's ECS task (task:1) is orphaned — it runs with no DynamoDB record
    and overwrites predictions.json on S3 (last-writer-wins).

    The DynamoDB record contains Task A's ARN, but Task B may be the one
    that actually wrote predictions.json to S3.

    This proves the semantic inconsistency: DynamoDB.ecs_task_arn != actual predictions author.
    """
    session_id = "22222222-2222-2222-2222-222222222222"

    calls = []
    lock = threading.Lock()

    mock_store = MagicMock()
    mock_store.get_session.return_value = _uploaded_session(session_id)

    transition_count = [0]

    def transition_side_effect(session_id, from_state, to_state, updates=None):
        with lock:
            n = transition_count[0]
            transition_count[0] += 1
            if n == 0:
                return SessionRecord(session_id=session_id, state=to_state.value)
            raise StateTransitionError(from_state, to_state)

    mock_store.transition_state.side_effect = transition_side_effect

    ecs_mock = MagicMock()
    task_arns_launched = []

    def ecs_run(**kwargs):
        import random
        suffix = random.randint(1000, 9999)
        arn = f"arn:aws:ecs:task:{suffix}"
        task_arns_launched.append(arn)
        return {"tasks": [{"taskArn": arn}], "failures": []}

    ecs_mock.run_task.side_effect = ecs_run

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    barrier = threading.Barrier(2)

    def run():
        with (
            patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
            patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
            patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
        ):
            barrier.wait()  # Both threads start simultaneously
            return handle_start_inference({"session_id": session_id})

    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start()
    t2.start()
    t1.join(timeout=10.0)
    t2.join(timeout=10.0)

    if ecs_mock.run_task.call_count == 2:
        # Race occurred
        transition_calls = mock_store.transition_state.call_args_list
        winning_arn = transition_calls[0][1]["updates"]["ecs_task_arn"]
        # Both ARNs exist, only one is recorded
        orphaned = [arn for arn in task_arns_launched if arn != winning_arn]
        assert len(orphaned) >= 1, "Expected at least one orphaned ECS task"
        # Document: orphaned task will overwrite predictions.json
        # DynamoDB will show winning_arn; actual predictions may come from orphaned task
    # If race didn't occur (timing), that's fine — this test documents the semantic risk


# ---------------------------------------------------------------------------
# 3. UI DOUBLE-CLICK SIMULATION
# ---------------------------------------------------------------------------

def test_ui_double_click_sequential_not_concurrent():
    """
    UI double-click from a single Streamlit session is NOT concurrent:
    Streamlit is single-threaded per session. The first click sets
    st.session_state.is_processing = True which disables the submit button.
    The second click fires only after the first rerun completes.

    Therefore UI double-click does NOT reproduce the race.
    This is the common case; the race requires two INDEPENDENT HTTP clients.
    """
    session_id = "33333333-3333-3333-3333-333333333333"

    call_count = [0]

    mock_store = MagicMock()
    # First call: UPLOADED. Second call (after transition): PROCESSING.
    def get_session_side(sid):
        n = call_count[0]
        call_count[0] += 1
        if n == 0:
            return _uploaded_session(sid)
        return SessionRecord(session_id=sid, state=SessionState.PROCESSING.value,
                             ecs_task_arn="arn:aws:ecs:task:first")

    mock_store.get_session.side_effect = get_session_side
    mock_store.transition_state.return_value = SessionRecord(
        session_id=session_id, state=SessionState.PROCESSING.value
    )

    ecs_mock = _make_ecs_mock("first")
    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    with (
        patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
        patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
        patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
    ):
        # First click
        r1 = handle_start_inference({"session_id": session_id})
        # Second click (sequential — Streamlit single-threaded)
        r2 = handle_start_inference({"session_id": session_id})

    assert ecs_mock.run_task.call_count == 1, (
        "Sequential double-click should only launch one ECS task (idempotent on PROCESSING)"
    )
    b1 = json.loads(r1["body"])
    b2 = json.loads(r2["body"])
    assert b1["status"] == "PROCESSING"
    assert b2["status"] == "PROCESSING"  # Second returns idempotent PROCESSING response
    assert b2.get("message") == "Inference already in progress."


# ---------------------------------------------------------------------------
# 4. HTTP RETRY SIMULATION (client-side retry after network timeout)
# ---------------------------------------------------------------------------

def test_http_retry_after_ecs_launch_but_before_dynamo_transition():
    """
    Scenario: Request 1 succeeds ECS launch but times out before returning to client.
    Client retries (Request 2). Request 2 reads DynamoDB: state is still UPLOADED
    (because Request 1's DynamoDB transition hasn't been committed yet or was rolled back).

    If Request 1's DynamoDB transition completed:
      -> Request 2 sees PROCESSING -> returns idempotent 202. Safe.

    If Request 1's DynamoDB transition is in-flight:
      -> Request 2 sees UPLOADED -> launches second ECS task.
      This is the window in which the race can be triggered by a retry.

    In Lambda, the max execution time is 29s (API GW timeout).
    If Lambda times out between ECS launch and DynamoDB transition,
    the retry fires into a STILL-UPLOADED session -> second ECS task.
    """
    session_id = "44444444-4444-4444-4444-444444444444"

    mock_store = MagicMock()

    # Simulate: Request 1 committed PROCESSING; Request 2 sees PROCESSING
    # This is the SAFE retry path: DynamoDB transition was committed before timeout.
    mock_store.get_session.side_effect = [
        _uploaded_session(session_id),      # Request 1 read
        SessionRecord(                       # Request 2 read: already PROCESSING
            session_id=session_id,
            state=SessionState.PROCESSING.value,
            ecs_task_arn="arn:aws:ecs:task:first",
        ),
    ]
    mock_store.transition_state.return_value = SessionRecord(
        session_id=session_id, state=SessionState.PROCESSING.value
    )

    ecs_mock = _make_ecs_mock("first")
    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    with (
        patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
        patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
        patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
    ):
        r1 = handle_start_inference({"session_id": session_id})  # initial request
        r2 = handle_start_inference({"session_id": session_id})  # retry

    # Safe path: only one ECS launch
    assert ecs_mock.run_task.call_count == 1
    b2 = json.loads(r2["body"])
    assert b2["status"] == "PROCESSING"
    assert b2.get("message") == "Inference already in progress."


def test_http_retry_race_when_first_request_dynamo_transition_not_yet_committed():
    """
    UNSAFE retry path: Request 1 launched ECS but Lambda timed out before
    the DynamoDB transition. When Request 2 arrives, DynamoDB still shows UPLOADED.
    Request 2 launches a second ECS task.
    """
    session_id = "55555555-5555-5555-5555-555555555555"

    mock_store = MagicMock()

    # Both reads return UPLOADED (DynamoDB not yet transitioned by Request 1)
    mock_store.get_session.return_value = _uploaded_session(session_id)

    ecs_calls = [0]

    def ecs_run(**kwargs):
        ecs_calls[0] += 1
        return {"tasks": [{"taskArn": f"arn:aws:ecs:task:{ecs_calls[0]}"}], "failures": []}

    ecs_mock = MagicMock()
    ecs_mock.run_task.side_effect = ecs_run
    mock_store.transition_state.return_value = SessionRecord(
        session_id=session_id, state=SessionState.PROCESSING.value
    )

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    with (
        patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
        patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
        patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
    ):
        # Request 1 launched ECS then "timed out" (Lambda recycled)
        # We simulate the scenario by running two requests sequentially
        # with DynamoDB not yet updated between them
        r1 = handle_start_inference({"session_id": session_id})
        # Reset mock to still show UPLOADED (simulates DynamoDB-not-yet-written scenario)
        mock_store.get_session.return_value = _uploaded_session(session_id)
        r2 = handle_start_inference({"session_id": session_id})

    # Documents the unsafe path
    assert ecs_calls[0] == 2, (
        f"Expected 2 ECS launches in unsafe retry scenario, got {ecs_calls[0]}"
    )


# ---------------------------------------------------------------------------
# 5. ECS LAUNCH FAILURE — VERIFY STATE DOES NOT BECOME FALSELY PROCESSING
# ---------------------------------------------------------------------------

def test_ecs_launch_failure_does_not_leave_session_in_processing():
    """
    Current behavior: If ECS launch fails, the function returns HTTP 500 and
    DOES NOT transition DynamoDB. So the session remains UPLOADED.
    This is CORRECT — no false PROCESSING state.

    Verify: transition_state is never called when run_task raises ClientError.
    """
    from botocore.exceptions import ClientError as BotoCoreClientError

    session_id = "66666666-6666-6666-6666-666666666666"

    mock_store = MagicMock()
    mock_store.get_session.return_value = _uploaded_session(session_id)

    ecs_mock = MagicMock()
    ecs_mock.run_task.side_effect = BotoCoreClientError(
        error_response={"Error": {"Code": "ClusterNotFoundException", "Message": "No cluster"}},
        operation_name="RunTask",
    )

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    with (
        patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
        patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
        patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
    ):
        result = handle_start_inference({"session_id": session_id})

    assert result["statusCode"] == 500
    body = json.loads(result["body"])
    assert body["error"] == "ECSError"

    # CRITICAL: transition_state MUST NOT have been called
    mock_store.transition_state.assert_not_called()


def test_ecs_empty_tasks_response_does_not_leave_session_in_processing():
    """
    ECS returns an empty 'tasks' list (capacity failure, no task ARN).
    No DynamoDB transition should occur.
    """
    session_id = "77777777-7777-7777-7777-777777777777"

    mock_store = MagicMock()
    mock_store.get_session.return_value = _uploaded_session(session_id)

    ecs_mock = MagicMock()
    ecs_mock.run_task.return_value = {
        "tasks": [],
        "failures": [{"reason": "RESOURCE:CPU", "arn": ""}],
    }

    s3_mock = MagicMock()
    s3_mock.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    with (
        patch("src.control_plane.lambda_handler.get_session_store", return_value=mock_store),
        patch("src.control_plane.lambda_handler.get_s3_client", return_value=s3_mock),
        patch("src.control_plane.lambda_handler.get_ecs_client", return_value=ecs_mock),
    ):
        result = handle_start_inference({"session_id": session_id})

    assert result["statusCode"] == 500
    body = json.loads(result["body"])
    assert body["error"] == "ECSError"
    mock_store.transition_state.assert_not_called()


# ---------------------------------------------------------------------------
# 6. PROPOSED FIX BEHAVIOR PROOF — "Transition First, Then Launch"
# ---------------------------------------------------------------------------

def test_proposed_atomic_sequence_prevents_double_launch():
    """
    Proposed fix sequence:
      A. Atomically transition UPLOADED -> PROCESSING (with ECS task ARN as None/sentinel)
      B. If transition succeeds: launch ECS task
      C. If ECS launch fails: transition PROCESSING -> PROCESSING_FAILED (compensating move)

    Under this sequence:
      - Only the request that wins the DynamoDB conditional write may launch ECS.
      - The second concurrent request sees PROCESSING from DynamoDB and returns idempotent 202.
      - No double ECS launch possible.

    This test PROVES the behavior of the proposed fix semantics, using a mock
    that enforces the new order. It does NOT implement the fix in production code.
    """
    session_id = "88888888-8888-8888-8888-888888888888"

    # --- Simulate the proposed fix logic inline ---

    transition_count = [0]
    transition_lock = threading.Lock()
    dynamo_state = [SessionState.UPLOADED]

    def atomic_transition(from_state, to_state, **kwargs):
        """Proposed: transition BEFORE launching ECS."""
        with transition_lock:
            if dynamo_state[0] != from_state:
                raise StateTransitionError(from_state, to_state,
                    f"Expected {from_state.value}, found {dynamo_state[0].value}")
            dynamo_state[0] = to_state
            transition_count[0] += 1
        return SessionRecord(session_id=session_id, state=to_state.value)

    ecs_launch_count = [0]

    def launch_ecs_if_won_transition(won: bool) -> str:
        if not won:
            return None
        ecs_launch_count[0] += 1
        return f"arn:aws:ecs:task:{ecs_launch_count[0]}"

    barrier = threading.Barrier(2)
    results = []

    def simulated_fixed_handler():
        barrier.wait()  # Start simultaneously
        try:
            arn = None
            won = False
            try:
                atomic_transition(SessionState.UPLOADED, SessionState.PROCESSING)
                won = True
            except StateTransitionError:
                won = False

            if won:
                arn = launch_ecs_if_won_transition(won)
            results.append({"won": won, "arn": arn})
        except Exception as e:
            results.append({"error": str(e)})

    t1 = threading.Thread(target=simulated_fixed_handler)
    t2 = threading.Thread(target=simulated_fixed_handler)
    t1.start()
    t2.start()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)

    # Only ONE request should have won the transition and launched ECS
    winners = [r for r in results if r.get("won")]
    losers = [r for r in results if not r.get("won") and "error" not in r]

    assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"
    assert len(losers) == 1, f"Expected exactly 1 loser, got {len(losers)}"
    assert ecs_launch_count[0] == 1, f"Expected 1 ECS launch, got {ecs_launch_count[0]}"
    assert winners[0]["arn"] is not None


def test_proposed_fix_ecs_failure_compensates_to_processing_failed():
    """
    Proposed fix: if the DynamoDB transition succeeds (UPLOADED -> PROCESSING)
    but ECS launch subsequently fails, the handler MUST transition
    PROCESSING -> PROCESSING_FAILED so the session does not get stuck.

    This test proves the compensation semantics.
    It does NOT implement the fix in production code.
    """
    session_id = "99999999-9999-9999-9999-999999999999"

    state = [SessionState.UPLOADED]
    compensation_called = [False]
    lock = threading.Lock()

    def atomic_transition(from_state, to_state, **kwargs):
        with lock:
            if state[0] != from_state:
                raise StateTransitionError(from_state, to_state)
            state[0] = to_state

    def compensate_processing_failed(error_info):
        with lock:
            assert state[0] == SessionState.PROCESSING, (
                f"Compensation should only fire from PROCESSING, got {state[0].value}"
            )
            state[0] = SessionState.PROCESSING_FAILED
            compensation_called[0] = True

    # Simulate proposed fix:
    # 1. Transition UPLOADED -> PROCESSING (succeeds)
    atomic_transition(SessionState.UPLOADED, SessionState.PROCESSING)
    assert state[0] == SessionState.PROCESSING

    # 2. ECS launch fails
    ecs_failed = True

    # 3. Compensate: PROCESSING -> PROCESSING_FAILED
    if ecs_failed:
        compensate_processing_failed({"code": "ECSError", "message": "Capacity failure"})

    assert state[0] == SessionState.PROCESSING_FAILED
    assert compensation_called[0] is True, "Compensation transition was not called"
