# Security Policy

## Supported Versions

This project is currently in active development for the Tech Challenge Fase 4 (FIAP/Alura).

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do Not Create a Public Issue
Please **do not** open a public issue or pull request that discloses the vulnerability, as this could allow malicious actors to exploit it before a fix is available.

### 2. Report via Email
Send an email to the project maintainers at:

- **contato@vagnerbarbosa.com**

Include the following information:
- **Description**: A clear description of the vulnerability
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Impact**: What could happen if exploited
- **Suggested Fix**: If you have a suggestion for fixing the issue
- **Your Contact**: How we can reach you for follow-up questions

### 3. Response Timeline

We will acknowledge receipt of your report within **48 hours** and provide a detailed response within **7 days**.

### 4. Disclosure Policy

Once a vulnerability is confirmed:
1. We will work on a fix and release it as soon as possible
2. We will credit you in the security advisory (unless you prefer to remain anonymous)
3. We will request a CVE if appropriate

## Security Measures

This project implements the following security measures:

### Code Security
- **Dependency Scanning**: GitHub Dependabot alerts enabled
- **Code Scanning**: CodeQL analysis for Python and GitHub Actions
- **Secret Scanning**: Enabled to prevent accidental secret commits

### Application Security
- **Input Validation**: All user inputs are validated before processing
- **LGPD Compliance**: Personal data is anonymized and temporary files are auto-deleted
- **Rate Limiting**: API endpoints have rate limits to prevent abuse
- **No Hardcoded Secrets**: All credentials use environment variables

### Infrastructure Security
- **Docker**: Non-root containers with minimal privileges
- **GitHub Actions**: Minimal required permissions for each workflow
- **Azure Services**: Secure configuration using managed identities where possible

## Security Best Practices for Users

1. **Environment Variables**: Never commit `.env` files or expose Azure credentials
2. **File Uploads**: The API validates file types and sizes (max 50MB)
3. **Audio/Video Processing**: Temporary files are automatically cleaned up
4. **Data Retention**: Analysis results can be cached temporarily; clear cache regularly

## Known Security Considerations

### ML Models (YOLOv8)
- Model files are downloaded from trusted sources (Ultralytics)
- Local inference prevents data exposure to external APIs

### Azure AI Services
- Credentials are never logged
- Rate limiting prevents quota exhaustion
- Token-based authentication only

## Security Updates

Security updates will be released as patch versions and announced in:
1. Release notes
2. Security advisories (when applicable)

---

**Last Updated**: April 2026

This security policy is subject to change. Please review periodically for updates.
