# PyPI Release Checklist

1. Update version in pyproject.toml.
2. Ensure README/README_CN and LICENSE are correct.
3. Build distributions:
   - python -m build
4. Verify artifacts:
   - twine check dist/*
5. Upload to PyPI:
   - twine upload dist/*
6. Test install:
   - pip install rhul-attendance-bot
   - rhul-attendance-bot

## Notes
- App data is stored under ~/.rhul_attendance_bot/profiles/<profile>.
- To uninstall: pip uninstall rhul-attendance-bot
