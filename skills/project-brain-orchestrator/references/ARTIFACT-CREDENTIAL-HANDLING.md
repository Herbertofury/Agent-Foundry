# Credential Handling

## Rules

- Prefer connected apps and existing authenticated CLIs.
- Never ask the user to paste a password, token, cookie, private key, or OAuth client secret into normal chat.
- Never place a secret directly in a command argument.
- Read secrets from environment variables or a platform credential store.
- Never write secrets into manifests, receipts, logs, ZIPs, Git commits, release notes, or error output.
- Redact authorization headers when debugging.
- Use least-privilege, repository-scoped, or file-scoped credentials.
- Delete temporary credentials and revoke one-time tokens after publication when appropriate.

## Information safe to request in chat

- provider name;
- repository owner/name;
- release tag and visibility;
- Drive folder ID;
- sharing email;
- upload endpoint documentation;
- required header names without values;
- response JSON path;
- desired public/private access.

## GitHub

Prefer `gh auth login` or the connected GitHub app. When a PAT is unavoidable, instruct the user to set it locally:

```bash
set GH_TOKEN=...
```

or:

```powershell
$env:GH_TOKEN = '...'
```

Do not echo the token afterward. Use a fine-grained PAT restricted to the exact repository and Contents write permission.

## Google Drive

Prefer the connected Google Drive app. For direct API use, configure OAuth locally and expose only a short-lived access token through `GOOGLE_DRIVE_ACCESS_TOKEN`. Do not store refresh tokens inside the skill directory.
