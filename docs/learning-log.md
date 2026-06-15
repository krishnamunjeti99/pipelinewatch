# Learning Log

## 2026-06-15 — Phase 0 complete

**What I did:**
- Created AWS account with root MFA enabled.
- Created a daily-use admin IAM user (krishna-admin) with MFA enabled.
- Configured AWS CLI in ap-south-1 (Mumbai) and verified with `aws sts get-caller-identity`.
- Set up WSL2 with Ubuntu, installed Python, Git, AWS CLI, Terraform, Docker.
- Created the project scaffolding at ~/projects/pipelinewatch.
- Set up SSH authentication with GitHub and pushed the initial commit.

**Concepts learned:**
- IAM root vs IAM user. Root is for billing emergencies only; daily work uses a least-privilege IAM user with MFA.
- Why MFA assignment requires an already-MFA-authenticated session (the chicken-and-egg bootstrap problem AWS solves by requiring root the first time).
- WSL2 file system performance: Linux home directory is fast, /mnt/c/ is slow.
- SSH key authentication for Git: ed25519 keys are modern and secure.

**Gotchas I hit:**
- "You need permissions" error when trying to assign MFA to my IAM user from that user's own session. Fix: do it from the root account, just once.
- Docker permission denied initially because my user wasn't in the docker group. Fix: `sudo usermod -aG docker $USER` and restart the shell.
- `code` command not found until VS Code + WSL extension were installed on Windows.

**Interview answers locked in:**

*Q: How do you secure an AWS account?*
- Enable MFA on the root account immediately.
- Never use root for daily work; create an admin IAM user with its own MFA.
- Never commit access keys; rotate them periodically.
- Use IAM roles (not users) for services and EC2 instances.
- Apply least-privilege: specify resources explicitly, avoid `"*"` in policies.
- Set billing alarms before any infrastructure is provisioned.

*Q: What's the difference between an IAM user and an IAM role?*
- A user has long-term credentials (password, access keys) and represents a person or external system.
- A role has no long-term credentials; it's assumed temporarily via STS, with short-lived session tokens.
- Services (Lambda, EC2, Glue) should use roles, never embedded user keys.