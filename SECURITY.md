# Security Policy

## IMPORTANT: Credential Management

**NEVER commit credentials to git!** All sensitive data must be stored in environment variables.

## Exposed Credentials Incident

### Date: December 31, 2025

**Issue**: The following credentials were accidentally exposed in the codebase:
- DeepSeek API Key
- Telegram Bot Token

**Action Taken**: 
- ✅ Removed hardcoded credentials from `config.py`
- ✅ All credentials now loaded from environment variables
- ⚠️ **IMPORTANT**: Credentials already in git history - need to rotate!

## Immediate Actions Required

### 1. Rotate Exposed Credentials

**Telegram Bot Token:**
1. Go to @BotFather on Telegram
2. Choose your bot
3. Use `/revoke` command to generate new token
4. Update your `.env` file with new token

**DeepSeek API Key:**
1. Go to https://platform.deepseek.com/
2. Navigate to API Keys section
3. Delete the exposed key: `sk-f0a38868c27748f1b782fab1db177d0f`
4. Generate new API key
5. Update your `.env` file with new key

### 2. Setup Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials:

```bash
TELEGRAM_BOT_TOKEN=your_new_telegram_token_here
DEEPSEEK_API_KEY=your_new_deepseek_key_here
```

### 3. Verify .env is in .gitignore

The `.gitignore` should include:
```
.env
config.local.json
```

## Security Best Practices

### For Development

1. **Use Environment Variables**
   - Never hardcode credentials in code
   - Use `os.getenv()` with safe defaults
   - Example: `os.getenv("API_KEY", "")`

2. **Separate Configs**
   - `.env.example` - Template (commit this)
   - `.env` - Actual credentials (NEVER commit)
   - `config.local.json` - Local overrides (NEVER commit)

3. **Git Hooks** (Optional)
   Add pre-commit hook to check for secrets:
   ```bash
   # .git/hooks/pre-commit
   git diff --cached | grep -E "sk-[a-zA-Z0-9]+" && exit 1
   ```

### For Production

1. **Use Secret Management**
   - Docker Secrets
   - Kubernetes Secrets
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

2. **Environment-Specific Configs**
   - Development: `.env.dev`
   - Staging: `.env.staging`
   - Production: `.env.prod` (from secure source)

3. **Regular Rotation**
   - Rotate API keys monthly/quarterly
   - After any suspected exposure
   - After team member changes

## Detecting Exposed Secrets

### Manual Check

```bash
# Check for API keys
grep -r "sk-" . --include="*.py" | grep -v ".git"

# Check for tokens
grep -r "token.*=" . --include="*.py" | grep -v ".git"

# Check for passwords
grep -r "password.*=" . --include="*.py" | grep -v ".git"
```

### Automated Tools

- **git-secrets**: https://github.com/awslabs/git-secrets
- **truffleHog**: https://github.com/trufflesecurity/trufflehog
- **gitleaks**: https://github.com/zricethezav/gitleaks

Install gitleaks:
```bash
brew install gitleaks  # macOS
# or
apt install gitleaks  # Linux
```

Scan repository:
```bash
gitleaks detect --source . --verbose
```

## What to Do If Secrets Are Exposed

1. **Immediate Actions**
   - Revoke/rotate all exposed credentials
   - Identify what was exposed
   - Check access logs for unauthorized usage

2. **Git History Cleanup** (if needed)
   ```bash
   # Remove from history (USE WITH CAUTION!)
   git filter-branch --tree-filter 'rm -f config.py' HEAD
   git push origin --force --all
   ```

3. **Prevent Future Exposure**
   - Add pre-commit hooks
   - Use automated scanning tools
   - Enable branch protection rules
   - Require code review for all changes

## Reporting Security Issues

If you find a security vulnerability, please:
1. Do NOT open a public issue
2. Email details to: security@yourdomain.com
3. Include steps to reproduce
4. Allow time to fix before disclosing

## Credit

Security issue reported by user - thank you for the vigilance! 🙏
