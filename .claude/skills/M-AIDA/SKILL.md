```markdown
# M-AIDA Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the M-AIDA TypeScript codebase. You will learn how to structure files, write imports and exports, follow commit message conventions, and organize and run tests. This guide ensures consistency and maintainability across contributions.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - **Example:**  
    ```plaintext
    user_profile.ts
    data_manager.test.ts
    ```

### Import Style
- Use **relative imports** for referencing modules within the project.
  - **Example:**  
    ```typescript
    import { fetchData } from './data_manager';
    ```

### Export Style
- Use **named exports** for all modules.
  - **Example:**  
    ```typescript
    // In data_manager.ts
    export function fetchData() { ... }
    ```

### Commit Messages
- Follow the **Conventional Commits** format.
- Prefix documentation changes with `docs:`.
- Keep commit messages concise (average 60 characters).
  - **Example:**  
    ```
    docs: update README with installation instructions
    ```

## Workflows

### Adding a New Module
**Trigger:** When you need to add a new feature or utility.
**Command:** `/add-module`

1. Create a new file using snake_case (e.g., `new_feature.ts`).
2. Write your code using named exports.
3. Use relative imports to include dependencies.
4. Add corresponding test files (e.g., `new_feature.test.ts`).
5. Commit your changes with a conventional commit message.

### Updating Documentation
**Trigger:** When you need to update or add documentation.
**Command:** `/update-docs`

1. Edit or create documentation files as needed.
2. Use the `docs:` prefix in your commit message.
3. Keep the message concise and descriptive.

## Testing Patterns

- Test files follow the pattern: `*.test.*` (e.g., `data_manager.test.ts`).
- The specific testing framework is not specified; check existing tests for structure.
- Place test files alongside the modules they test or in a dedicated test directory.
- Example test file:
  ```typescript
  // data_manager.test.ts
  import { fetchData } from './data_manager';

  test('fetchData returns expected result', () => {
    // ...test implementation
  });
  ```

## Commands
| Command         | Purpose                                   |
|-----------------|-------------------------------------------|
| /add-module     | Scaffold and add a new module             |
| /update-docs    | Update or add documentation               |
```
