# euron-agenteval

Python client and CLI for [Euron Open AgentEval](../../README.md): register an agent, run
it against a versioned dataset, and compare runs over time, against a running AgentEval
server. Depends on the `agenteval` package (`apps/api`) as an editable path dependency, so
the SDK's dataclasses and span shapes are always the real ones the server scores against,
never a hand-copied duplicate.

```python
from agenteval_sdk import AgentEval

evaluator = AgentEval(api_url="http://localhost:5730", api_key="aek_...", org_id="...")

result = evaluator.evaluate(
    agent="my_pkg.agent:answer",   # or an http:// endpoint URL, or a local callable
    dataset="customer-support-tests",
    metrics=["exact_match", "task_success"],
)
print(result.summary())
```

The CLI mirrors the same client:

```
agenteval-cli init
agenteval-cli agent add
agenteval-cli dataset create
agenteval-cli evaluate run
agenteval-cli compare
agenteval-cli report export
```
