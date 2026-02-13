import re

pattern = r"(?i)(execute|cursor\.execute)\s*\(\s*['\"]SELECT.*['\"]\s*\+\s*"
test_string = "query = 'SELECT * FROM users WHERE id = ' + user_input"

print(f"Pattern: {pattern}")
print(f"String: {test_string}")

match = re.search(pattern, test_string)
if match:
    print("✅ MATCHED!")
else:
    print("❌ NO MATCH")

# Wait, the pattern LOOKS for 'execute(' or 'cursor.execute('
# But the test string is just assigning a string variable 'query = ...'
# The vulnerability is the STRING CONCATENATION itself, not necessarily the execute call (though execute call is where it happens usually).
# But often we want to catch the variable assignment too if it looks like SQL.

# My test case in test_sast.py was:
# f.write("query = 'SELECT * FROM users WHERE id = ' + user_input")

# My regex requires 'execute(...)'. That's why it failed.
# I should broaden the regex or update the test case to actually CALL execute.
# Let's broaden the regex to catch string concatenation with SQL keywords.
