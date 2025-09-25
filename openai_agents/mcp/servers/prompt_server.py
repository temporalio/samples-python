from mcp.server.fastmcp import FastMCP

# Create server
mcp = FastMCP("Prompt Server")


# Instruction-generating prompts (user-controlled)
@mcp.prompt()
def generate_code_review_instructions(
    focus: str = "general code quality", language: str = "python"
) -> str:
    """Generate agent instructions for code review tasks"""
    print(f"[debug-server] generate_code_review_instructions({focus}, {language})")

    return f"""You are a senior {language} code review specialist. Your role is to provide comprehensive code analysis with focus on {focus}.

INSTRUCTIONS:
- Analyze code for quality, security, performance, and best practices
- Provide specific, actionable feedback with examples
- Identify potential bugs, vulnerabilities, and optimization opportunities
- Suggest improvements with code examples when applicable
- Be constructive and educational in your feedback
- Focus particularly on {focus} aspects

RESPONSE FORMAT:
1. Overall Assessment
2. Specific Issues Found
3. Security Considerations
4. Performance Notes
5. Recommended Improvements
6. Best Practices Suggestions

Use the available tools to check current time if you need timestamps for your analysis."""


@mcp.prompt()
def generate_review_rubric(target: str = "application code") -> str:
    """Generate a scoring rubric for reviewing code or plans"""
    return f"""You are evaluating {target}. Score each category 1-5 and justify briefly.

CATEGORIES:
- Correctness and Reliability
- Security and Risk
- Performance and Efficiency
- Readability and Maintainability
- Testability and Coverage
- Compliance with Style/Guidelines

FORMAT:
- Overall Score (1-5)
- Category Scores (bulleted)
- Top 3 Issues (with impact level and suggested fix)
- Quick Wins (3 bullets)
"""


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
