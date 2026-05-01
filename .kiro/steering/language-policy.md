---
inclusion: always
---

# Language Policy

## All Artifacts Must Be Written in English [en-US]

Every artifact produced by agents must be written in **American English (en-US)**, regardless of the language used by the user in conversation.

## Scope

This applies to all generated or modified artifacts, including:

- Source code (variable names, function names, class names, comments, docblocks)
- Spec files (`requirements.md`, `design.md`, `tasks.md`)
- Steering files
- Git commit messages
- Git branch names
- Git tags
- Configuration files
- Documentation and README files
- Log messages and error messages in code
- Database schema names, column names, and comments
- API endpoint names and descriptions

## Rules

- **Code**: All identifiers, comments, and inline documentation must be in en-US
- **Spec documents**: All content in requirements, design, and tasks files must be in en-US
- **Commit messages**: Always written in en-US
- **User-facing strings**: If the application supports i18n, the default/fallback locale must be en-US
- **Conversation**: Agents may respond to the user in their preferred language, but all artifacts must still be produced in en-US

## Example

```php
// ✅ Correct
// Calculate the total price including taxes
public function calculateTotalPrice(float $basePrice): float {}

// ❌ Incorrect
// Calcula o preço total incluindo impostos
public function calcularPrecoTotal(float $precoBase): float {}
```
