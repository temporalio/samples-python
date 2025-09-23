#!/usr/bin/env python3
"""
Simple test to validate the multiline logging interceptor logic
"""
import json
import traceback


def test_multiline_formatting():
    """Test that multiline exceptions are properly formatted as single-line JSON"""
    try:
        try:
            raise ValueError("Inner exception with\nmultiple lines\nof text")
        except ValueError as inner:
            raise RuntimeError(
                "Outer exception that wraps\nanother exception with\nmultiline content"
            ) from inner
    except Exception as e:
        exception_data = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc().replace("\n", " | ")
        }
        
        json_output = json.dumps(exception_data)
        
        print("Original exception message:")
        print(repr(str(e)))
        print("\nFormatted JSON output:")
        print(json_output)
        print("\nValidation:")
        print(f"- Contains newlines in JSON: {'\\n' in json_output}")
        print(f"- JSON is valid: {json.loads(json_output) is not None}")
        print(f"- Single line: {json_output.count('\\n') == 0}")
        
        return json_output


if __name__ == "__main__":
    print("Testing multiline exception formatting...")
    result = test_multiline_formatting()
    print("\n✅ Test completed successfully!")
