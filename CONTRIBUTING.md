# Contributing to Zenith AI

Thank you for your interest in contributing to Zenith AI! This document provides guidelines and instructions for contributing.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Screenshots if applicable

### Suggesting Features

Feature suggestions are welcome! Please:
- Check existing issues to avoid duplicates
- Clearly describe the feature and its benefits
- Explain the use case
- Provide examples if possible

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/zenith-ai.git
   cd zenith-ai
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clean, readable code
   - Follow the existing code style
   - Add comments where necessary
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Run the application
   cd zenith
   python main.py
   
   # Test your feature thoroughly
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: description of your changes"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template
   - Submit for review

## 📝 Code Style Guidelines

### Python
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and concise
- Use meaningful variable names

Example:
```python
async def process_message(
    user_id: str,
    session_id: str,
    message: str
) -> dict:
    """
    Process a user message through the AI pipeline.
    
    Args:
        user_id: User's unique identifier
        session_id: Conversation session ID
        message: The user's message
        
    Returns:
        Response dictionary with text and metadata
    """
    # Implementation here
    pass
```

### JavaScript/TypeScript
- Use ES6+ features
- Follow Airbnb style guide
- Use async/await over promises when possible
- Add JSDoc comments for complex functions

### Documentation
- Update README.md if adding new features
- Add inline comments for complex logic
- Keep documentation up-to-date

## 🧪 Testing

Before submitting a PR:
- Test your changes locally
- Ensure no existing functionality is broken
- Test edge cases
- Verify error handling works correctly

## 🔒 Security

- Never commit sensitive data (API keys, credentials, etc.)
- Use `.env` files for configuration
- Report security vulnerabilities privately

## 📋 Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add: New feature description
Fix: Bug fix description
Update: Changes to existing feature
Refactor: Code restructuring
Docs: Documentation changes
Style: Formatting changes
Test: Adding tests
```

Examples:
```
Add: Voice assistant functionality with Web Speech API
Fix: Firestore index error in notes query
Update: Gemini model to 2.5-flash
Docs: Add API endpoint documentation
```

## 🏗️ Development Setup

1. **Install dependencies**
   ```bash
   cd zenith
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run in development mode**
   ```bash
   uvicorn main:app --reload
   ```

## 📦 Adding Dependencies

If adding new dependencies:
1. Add to `requirements.txt`
2. Document why it's needed
3. Ensure it's compatible with Python 3.10+
4. Test installation on clean environment

## 🎯 Areas for Contribution

We especially welcome contributions in:
- 🐛 Bug fixes
- 📝 Documentation improvements
- 🎨 UI/UX enhancements
- ✨ New integrations (Slack, Discord, etc.)
- 🔧 Performance optimizations
- 🧪 Test coverage
- 🌍 Internationalization

## ❓ Questions?

Feel free to:
- Open an issue for questions
- Join discussions
- Ask for clarification on anything

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Zenith AI!** 🚀
