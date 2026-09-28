# Adaptive Routing and Backpressure

## Contents

- Failure classes
- Concurrency control
- Backpressure memory

Load this reference only when a connector/tool route fails, throttles, times out, or rejects payload size. The goal is to change strategy once, not burn time repeating the same failure.

## Failure classes

### Deterministic capability failure

Examples: no outbound DNS, network unreachable in a known sandbox, unsupported operation, unavailable connector capability.

Action:

1. record the route as unavailable for the current environment;
2. switch to a native connector, materialized file, or other supported route;
3. do not retry until the environment or evidence changes.

### Authentication or permission failure

Examples: 401/403, missing scope, protected branch/Drive permission.

Action:

1. preserve all completed independent work;
2. try another already-authorized route only if equivalent and permitted;
3. otherwise surface the exact user-only authorization/action needed;
4. do not loop unchanged credentials or permission calls.

### Validation/input failure

Examples: wrong argument name, malformed ID, invalid range, unsupported field combination.

Action:

1. use the returned schema/error to fix the payload;
2. retry the corrected call once;
3. cache the corrected contract so later calls do not repeat the mistake.

### Payload/size/complexity limit

Examples: request too large, batch too large, export limit, response-size failure.

Action:

1. preserve successful/partial sub-results;
2. split the batch roughly in half or at an explicit provider limit;
3. continue with the fewest safe sub-batches;
4. remember the discovered safe size for the run;
5. do not degrade immediately to one-item calls unless required.

### Rate limit / throttling

Examples: 429, "too many requests", quota/backpressure message, provider Retry-After.

Action:

1. stop adding pressure to the same route;
2. honor explicit retry guidance when available, measuring the wait from the failed response/completion;
3. perform independent local/other-provider work instead of busy waiting;
4. reduce concurrency or batch pressure for the next wave;
5. increase pressure cautiously only after clean waves (AIMD-like adaptation);
6. reuse already-returned IDs/results rather than rediscovery.

### Transient provider/network failure

Examples: isolated timeout, 5xx, connection reset with no deterministic environment failure.

Action:

1. keep partial output if any;
2. continue independent work;
3. retry only once conditions plausibly changed, or use an alternate equivalent route;
4. avoid identical immediate retries.

### Truncated/partial output

Examples: display truncation, response resource URI, continuation cursor, next-read pointer.

Action:

1. treat returned content as successful partial work;
2. use the cursor/resource/range continuation;
3. target the missing segment;
4. do not rerun the entire producer solely to remove truncation.

## Concurrency control

Prefer in order:

1. one native bulk/batch call;
2. a bounded wave of independent calls within known provider/tool limits;
3. smaller waves after throttling;
4. serial only where dependencies or provider limits require it.

Do not use duplicate speculative requests as a latency hedge for stateful or consequential operations. Never hedge mutations.

## Backpressure memory

Retain a compact per-route note during the run:

`route -> failure class -> learned safe batch/concurrency -> retry eligibility/change condition -> last valid identifiers`

This avoids rediscovering the same limit or retrying the same dead path later in the conversation.
