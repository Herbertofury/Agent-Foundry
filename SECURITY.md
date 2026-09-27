# Security Policy

Agent Foundry includes agent instructions, Skills, runtime-control guidance, and installable bundles. Security reports are welcome for issues that could cause unsafe execution, privilege escalation, prompt/control bypass, data exposure, malicious Skill installation, provenance confusion, or false security claims.

## Report privately

Please use GitHub's private vulnerability reporting for the Agent Foundry repository when available. Do not publish working exploit details, credentials, private data, or malicious Skill payloads in a public issue before a fix or disclosure plan exists.

## In scope

Examples:
- a Foundry rule/tool that authorizes more than intended;
- bypass of third-party Skill quarantine or verification;
- a malicious bundle accepted as trusted;
- provenance/digest mismatch not detected;
- secret leakage through logs/evals/telemetry;
- workflow permissions broader than required;
- runtime control bypass;
- cross-skill privilege escalation;
- unsafe update/sync behavior.

## Security philosophy

- prompt text is not a sufficient security boundary;
- automated scanners are evidence, not certification;
- permissions should be least-privilege;
- important releases should be provenance-verifiable;
- high-impact actions need explicit authorization/enforcement boundaries;
- third-party Skills start untrusted.
