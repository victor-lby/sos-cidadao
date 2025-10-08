# License Compliance Documentation

This document outlines the licensing compliance for the S.O.S Cidadão project.

## Project License

S.O.S Cidadão is licensed under the **Apache License 2.0**.

- **License File**: [LICENSE](../LICENSE)
- **SPDX Identifier**: `Apache-2.0`
- **License URL**: https://www.apache.org/licenses/LICENSE-2.0

## SPDX License Identifiers

All source files include SPDX license identifiers as recommended by the [SPDX specification](https://spdx.dev/):

### Python Files
```python
# SPDX-License-Identifier: Apache-2.0
```

### TypeScript/JavaScript Files
```typescript
/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2024 S.O.S Cidadão Contributors
 */
```

### YAML/Configuration Files
```yaml
# SPDX-License-Identifier: Apache-2.0
```

## Third-Party Dependencies

### Backend Dependencies (Python)

All Python dependencies are Apache 2.0 compatible:

| Package | License | Compatibility |
|---------|---------|---------------|
| Flask | BSD-3-Clause | ✅ Compatible |
| Pydantic | MIT | ✅ Compatible |
| PyJWT | MIT | ✅ Compatible |
| pymongo | Apache-2.0 | ✅ Compatible |
| redis | MIT | ✅ Compatible |
| pika | BSD-3-Clause | ✅ Compatible |
| opentelemetry-api | Apache-2.0 | ✅ Compatible |
| pytest | MIT | ✅ Compatible |

### Frontend Dependencies (Node.js)

All Node.js dependencies are Apache 2.0 compatible:

| Package | License | Compatibility |
|---------|---------|---------------|
| Vue 3 | MIT | ✅ Compatible |
| Vuetify 3 | MIT | ✅ Compatible |
| Vue Router | MIT | ✅ Compatible |
| Pinia | MIT | ✅ Compatible |
| TypeScript | Apache-2.0 | ✅ Compatible |
| Vite | MIT | ✅ Compatible |
| Axios | MIT | ✅ Compatible |

## License Compatibility Matrix

The Apache 2.0 license is compatible with:

- ✅ **MIT License**: Can include MIT-licensed code
- ✅ **BSD Licenses**: Can include BSD-licensed code
- ✅ **Apache 2.0**: Can include other Apache 2.0 code
- ✅ **ISC License**: Can include ISC-licensed code
- ❌ **GPL Licenses**: Cannot include GPL-licensed code (copyleft conflict)
- ❌ **AGPL Licenses**: Cannot include AGPL-licensed code

## Dependency License Verification

### Automated Checking

We use automated tools to verify license compatibility:

```bash
# Python dependencies
pip-licenses --format=table --order=license

# Node.js dependencies
npx license-checker --summary
```

### Manual Review Process

1. **New Dependency Addition**: All new dependencies must be reviewed for license compatibility
2. **License Documentation**: Document the license of each new dependency
3. **Compatibility Check**: Verify compatibility with Apache 2.0
4. **Approval Required**: License team approval required for any non-standard licenses

## Copyright Attribution

### Project Copyright

```
Copyright 2024 S.O.S Cidadão Contributors
```

### Third-Party Attributions

Third-party libraries retain their original copyright notices. See individual package files for specific attributions.

## Contribution License Agreement

### Developer Certificate of Origin (DCO)

Contributors must sign off on their commits using the Developer Certificate of Origin:

```bash
git commit -s -m "feat: add new feature"
```

This adds a `Signed-off-by` line certifying that the contributor has the right to submit the code under the project's license.

### Contribution Process

1. **Fork the repository**
2. **Make changes** following coding standards
3. **Add SPDX identifiers** to new files
4. **Sign commits** with DCO
5. **Submit pull request**

## License Headers

### Required Headers

All source files must include appropriate license headers:

#### Python Files
```python
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 S.O.S Cidadão Contributors

"""
Module description here.
"""
```

#### TypeScript/JavaScript Files
```typescript
/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2024 S.O.S Cidadão Contributors
 */

// Module code here
```

#### Configuration Files
```yaml
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 S.O.S Cidadão Contributors

# Configuration content here
```

### Exceptions

The following files do not require license headers:
- Generated files (build outputs, compiled code)
- Package manager files (package.json, requirements.txt)
- Documentation files (README.md, unless substantial original content)
- Configuration files with minimal content

## Compliance Verification

### Pre-commit Hooks

License compliance is verified through pre-commit hooks:

```bash
# Install pre-commit hooks
pre-commit install

# Run license checks
pre-commit run license-check --all-files
```

### CI/CD Pipeline

The CI/CD pipeline includes license compliance checks:

1. **SPDX Identifier Verification**: Ensures all source files have proper identifiers
2. **Dependency License Check**: Verifies all dependencies are compatible
3. **Copyright Notice Validation**: Checks for proper copyright attribution

### Manual Audit

Periodic manual audits are conducted to ensure:
- All dependencies are properly documented
- License compatibility is maintained
- Copyright notices are up to date
- SPDX identifiers are present and correct

## License Violations

### Reporting

License violations should be reported to the project maintainers:
- **Email**: [maintainers@sos-cidadao.org]
- **GitHub Issues**: Use the "license-violation" label

### Resolution Process

1. **Investigation**: Review the reported violation
2. **Assessment**: Determine the scope and impact
3. **Remediation**: Remove incompatible code or obtain proper licensing
4. **Documentation**: Update compliance documentation
5. **Prevention**: Implement measures to prevent future violations

## Resources

- [Apache License 2.0 Full Text](https://www.apache.org/licenses/LICENSE-2.0)
- [SPDX License List](https://spdx.org/licenses/)
- [License Compatibility Guide](https://www.apache.org/legal/resolved.html)
- [Developer Certificate of Origin](https://developercertificate.org/)

## Contact

For license-related questions:
- **Project Maintainers**: [GitHub Team](https://github.com/orgs/your-org/teams/maintainers)
- **Legal Questions**: Consult with your organization's legal team

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Reviewed By**: Project Maintainers