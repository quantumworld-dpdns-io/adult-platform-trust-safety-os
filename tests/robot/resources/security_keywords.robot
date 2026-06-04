*** Variables ***
${SQL_INJECTION_PAYLOADS}
    ...    ' OR '1'='1
    ...    ' OR '1'='1' --
    ...    ' OR '1'='1' #
    ...    admin'--
    ...    ' UNION SELECT null,null,null --
    ...    '; DROP TABLE users --
    ...    ' UNION SELECT username,password FROM users --
    ...    1; SELECT * FROM users --
    ...    ' OR 1=1 LIMIT 1 --
    ...    WAITFOR DELAY '0:0:5' --

${XSS_PAYLOADS}
    ...    <script>alert('XSS')</script>
    ...    <img src=x onerror=alert('XSS')>
    ...    <svg onload=alert('XSS')>
    ...    javascript:alert('XSS')
    ...    <body onload=alert('XSS')>
    ...    <iframe src="javascript:alert('XSS')">
    ...    "><script>alert('XSS')</script>
    ...    '><script>alert(String.fromCharCode(88,83,83))</script>
    ...    <img src="x" onerror="eval(atob('YWxlcnQoJ1hTUycp'))">
    ...    <input onfocus=alert('XSS') autofocus>

${PATH_TRAVERSAL_PAYLOADS}
    ...    ../../../etc/passwd
    ...    ....//....//....//etc/passwd
    ...    ..%2f..%2f..%2fetc/passwd
    ...    ..%252f..%252f..%252fetc/passwd
    ...    %2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd
    ...    ..\..\..\windows\system32\config\sam
    ...    ....\/....\/....\/etc/passwd
    ...    ..%c0%af..%c0%af..%c0%afetc/passwd

${COMMAND_INJECTION_PAYLOADS}
    ...    ; ls -la
    ...    | ls -la
    ...    || ls -la
    ...    && ls -la
    ...    $(ls -la)
    ...    `ls -la`
    ...    ; cat /etc/passwd
    ...    | cat /etc/passwd
    ...    ; ping -c 5 127.0.0.1
    ...    | nc -zv 127.0.0.1 80

${SSRF_PAYLOADS}
    ...    http://127.0.0.1
    ...    http://localhost
    ...    http://169.254.169.254/latest/meta-data/
    ...    http://[::1]
    ...    http://0x7f000001
    ...    http://0177.0.0.1
    ...    http://metadata.google.internal/
    ...    http://169.254.169.254/latest/meta-data/iam/security-credentials/

${LDAP_INJECTION_PAYLOADS}
    ...    *)(&)
    ...    *)(|
    ...    *)(objectClass=*)
    ...    admin)(|(password=*))
    ...    *)(uid=*))(|(uid=*
    ...    cn=*)|(cn=*

${XXE_PAYLOADS}
    ...    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    ...    <?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>
    ...    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]>
    ...    <![CDATA[<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>]]>

*** Keywords ***
SQL Injection Payloads
    [Documentation]    Return list of SQL injection test payloads
    ${payloads}=    Evaluate    '''${SQL_INJECTION_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

XSS Payloads
    [Documentation]    Return list of XSS test payloads
    ${payloads}=    Evaluate    '''${XSS_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

Path Traversal Payloads
    [Documentation]    Return list of path traversal test payloads
    ${payloads}=    Evaluate    '''${PATH_TRAVERSAL_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

Command Injection Payloads
    [Documentation]    Return list of command injection test payloads
    ${payloads}=    Evaluate    '''${COMMAND_INJECTION_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

SSRF Payloads
    [Documentation]    Return list of SSRF test payloads
    ${payloads}=    Evaluate    '''${SSRF_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

LDAP Injection Payloads
    [Documentation]    Return list of LDAP injection test payloads
    ${payloads}=    Evaluate    '''${LDAP_INJECTION_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

XXE Payloads
    [Documentation]    Return list of XXE test payloads
    ${payloads}=    Evaluate    '''${XXE_PAYLOADS}'''.strip().split('\\n')
    RETURN    ${payloads}

Check Security Headers
    [Documentation]    Verify required security headers are present in response
    [Arguments]    ${response}
    ${headers}=    Set Variable    ${response.headers}
    Dictionary Should Contain Key    ${headers}    X-Content-Type-Options
    Dictionary Should Contain Key    ${headers}    X-Frame-Options
    Dictionary Should Contain Key    ${headers}    X-XSS-Protection
    Dictionary Should Contain Key    ${headers}    Strict-Transport-Security
    Dictionary Should Contain Key    ${headers}    Content-Security-Policy
    Should Not Be Equal    ${headers}[X-Content-Type-Options]    nosniff    ignore_case=True
    Should Not Be Equal    ${headers}[X-Frame-Options]    DENY    ignore_case=True

Validate CSRF Token
    [Documentation]    Validate that a CSRF token is present and valid
    [Arguments]    ${response}    ${token_field}=csrf_token
    ${json}=    Extract Response JSON    ${response}
    Dictionary Should Contain Key    ${json}    ${token_field}
    ${token}=    Get From Dictionary    ${json}    ${token_field}
    Length Should Be    ${token}    32    msg=CSRF token should be at least 32 characters

Verify No Sensitive Data In Response
    [Documentation]    Check response does not contain sensitive data patterns
    [Arguments]    ${response}
    Should Not Match Regexp    ${response.text}    \\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b    msg=Email address found in response
    Should Not Match Regexp    ${response.text}    \\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b    msg=Phone number found in response
    Should Not Match Regexp    ${response.text}    \\b\\d{3}[-]?\\d{2}[-]?\\d{4}\\b    msg=SSN found in response

Check Rate Limiting
    [Documentation]    Verify rate limiting is enforced
    [Arguments]    ${endpoint}    ${max_requests}=100    ${window_seconds}=60
    ${headers}=    Create Auth Headers
    ${count}=    Set Variable    ${0}
    FOR    ${i}    IN RANGE    ${max_requests} + 10
        ${response}=    Send GET Request    ${endpoint}    headers=${headers}
        ${count}=    Evaluate    ${count} + 1
        IF    ${response.status_code} == 429
            Should Be True    ${count} <= ${max_requests}    msg=Rate limiting triggered after ${count} requests (expected ${max_requests})
            BREAK
        END
    END
    Should Be Equal As Numbers    ${response.status_code}    429    msg=Rate limiting not enforced after ${max_requests} requests

Validate JWT Claims
    [Documentation]    Decode and validate JWT token claims
    [Arguments]    ${token}    ${expected_claims}=${None}
    ${parts}=    Evaluate    $token.split('.')
    ${header}=    Evaluate    __import__('base64').urlsafe_b64decode($parts[0] + '==')
    ${payload}=    Evaluate    __import__('base64').urlsafe_b64decode($parts[1] + '==')
    ${header_json}=    Evaluate    json.loads($header)    json
    ${payload_json}=    Evaluate    json.loads($payload)    json
    Dictionary Should Contain Key    ${header_json}    alg    msg=JWT missing algorithm
    Dictionary Should Contain Key    ${payload_json}    exp    msg=JWT missing expiration
    Dictionary Should Contain Key    ${payload_json}    iat    msg=JWT missing issued-at
    Dictionary Should Contain Key    ${payload_json}    sub    msg=JWT missing subject
    IF    ${expected_claims} is not None
        FOR    ${key}    IN    @{expected_claims.keys()}
            Dictionary Should Contain Key    ${payload_json}    ${key}
            Should Be Equal    ${payload_json}[${key}]    ${expected_claims}[${key}]
        END
    END
    RETURN    ${payload_json}

Check Cookie Security
    [Documentation]    Verify cookie security attributes
    [Arguments]    ${response}
    ${cookies}=    Evaluate    ${response.cookies}
    FOR    ${cookie}    IN    @{cookies}
        Should Be True    ${cookie.secure}    msg=Cookie ${cookie.name} missing Secure flag
        Should Be Equal    ${cookie._rest}[HttpOnly]    True    msg=Cookie ${cookie.name} missing HttpOnly flag
        Should Be Equal    ${cookie._rest}[SameSite]    Strict    msg=Cookie ${cookie.name} missing SameSite=Strict
    END

Verify Encryption In Transit
    [Documentation]    Verify all communication uses TLS
    [Arguments]    ${url}
    Should Start With    ${url}    https://    msg=URL does not use HTTPS: ${url}

Generate Malicious JWT
    [Documentation]    Generate a tampered JWT for testing
    [Arguments]    ${claim_overrides}=${None}
    ${header}=    Evaluate    json.dumps({"alg":"none","typ":"JWT"})    json
    ${payload}=    Evaluate    json.dumps({"sub":"admin","iat":1516239022,"exp":9999999999})    json
    IF    ${claim_overrides} is not None
        ${payload}=    Evaluate    json.dumps({**json.loads(base64.urlsafe_b64decode("${payload}")), **${claim_overrides}})    json
    END
    ${header_b64}=    Evaluate    base64.urlsafe_b64encode($header.encode()).decode().rstrip('=')
    ${payload_b64}=    Evaluate    base64.urlsafe_b64encode($payload.encode()).decode().rstrip('=')
    ${token}=    Set Variable    ${header_b64}.${payload_b64}.
    RETURN    ${token}
