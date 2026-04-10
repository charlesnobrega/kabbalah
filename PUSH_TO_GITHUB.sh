#!/bin/bash

# Kabbalah - Push to GitHub Script
# This script pushes the Kabbalah project to GitHub

echo "🚀 Kabbalah - Pushing to GitHub"
echo "================================"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📝 Initializing git repository..."
    git init
fi

# Add all files
echo "📦 Adding all files..."
git add .

# Commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Kabbalah specification and setup

- Complete specifications (16 requirements, 109 criteria)
- Comprehensive design (14 components)
- Detailed implementation tasks (167 tasks, 11 phases)
- Full documentation and guides
- Configuration templates
- Contribution guidelines"

# Add remote
echo "🔗 Adding GitHub remote..."
git remote add origin https://github.com/charlesnobrega/kabbalah.git 2>/dev/null || git remote set-url origin https://github.com/charlesnobrega/kabbalah.git

# Rename branch to main
echo "🌿 Renaming branch to main..."
git branch -M main

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo ""
echo "📊 Next steps:"
echo "1. Go to https://github.com/charlesnobrega/kabbalah"
echo "2. Configure GitHub settings (see GITHUB_SETUP.md)"
echo "3. Create project board and milestones"
echo "4. Start Phase 1 implementation"
echo ""
echo "📚 Documentation:"
echo "- README.md - Project overview"
echo "- CONTRIBUTING.md - Contribution guidelines"
echo "- docs/specs/requirements.md - Requirements"
echo "- docs/specs/design.md - Architecture"
echo "- docs/specs/tasks.md - Implementation tasks"
echo ""
