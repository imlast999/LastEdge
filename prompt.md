The audit confirmed that P5.3 is very close to completion, but it is still a Process & Resource Health Monitor rather than a complete Long Forward Validation system.

I want to close P5.3 properly before moving to P5.4.

Please implement ONLY the improvements identified by the audit.

Do not redesign the architecture.
Do not introduce unnecessary complexity.
Reuse the existing services wherever possible.

Required improvements:

1. Session persistence
- Create a persistent long_forward_sessions table.
- Store:
  - session_id
  - profile (24h / 72h / 7d)
  - status (ACTIVE, COMPLETED, ABORTED, INTERRUPTED)
  - start_time
  - end_time
  - final_verdict
  - summary_json
- On startup, automatically detect abandoned ACTIVE sessions and mark them as INTERRUPTED.

2. Trading integration
Extend LongForwardValidationService so each validation session automatically includes:
- generated signals
- executed trades
- rejected orders
- missed executions (when possible)
- equity evolution
- floating PnL evolution
- maximum drawdown
- execution statistics (reuse ExecutionAnalyticsService whenever possible)

Do not duplicate logic that already exists elsewhere.

3. MT5 downtime tracking
Integrate LongForwardValidationService with reconnection_system.py.

Automatically record:
- disconnect timestamp
- reconnect timestamp
- downtime duration
- total reconnect count

No manual calls should be required.

4. Historical session explorer
Implement:
- CLI:
  python run_long_forward_validation.py --list
  python run_long_forward_validation.py --session <id>

- REST API:
  GET /api/system/long-forward-validation/history
  GET /api/system/long-forward-validation/<session_id>

Allow previous sessions to be inspected after they have finished.

5. Forward Validation Score
Implement a final quantitative score (0–100) summarizing the overall quality of the validation session.

The score should be calculated from real metrics such as:
- uptime
- MT5 disconnects
- downtime
- recovered failures
- unrecovered failures
- rejected orders
- execution quality
- drawdown
- memory stability
- anomaly severity

The exact weights are up to you, but document the calculation clearly.

After implementation:

- execute the complete unit test suite;
- add any new tests required;
- verify that all data comes from real services (no placeholders or mocked values);
- perform a final honest audit of P5.3;
- if every roadmap requirement is now satisfied, explicitly declare P5.3 officially CLOSED.

Finally:
- create a git commit with a clear message;
- push everything to GitHub.