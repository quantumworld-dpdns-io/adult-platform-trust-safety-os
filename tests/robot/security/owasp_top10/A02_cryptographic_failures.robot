*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    OperatingSystem
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Crypto Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    30s

*** Test Cases ***
Weak Cipher Detection
    [Documentation]    A02:1 - Detect weak cipher suites in TLS connections
    [Tags]    owasp    a02    cipher
    ${weak_ciphers}=    Create List    DES    3DES    RC4    MD5    NULL    EXPORT
    ${response}=    Send GET Request    /api/v1/health
    ${cipher}=    Get From Dictionary    ${response.headers}    X-TLS-Cipher    default=${EMPTY}
    FOR    ${weak}    IN    @{weak_ciphers}
        Should Not Contain    ${cipher}    ${weak}    msg=Weak cipher detected: ${cipher}
    END

TLS Version Check
    [Documentation]    A02:2 - Verify only TLS 1.2+ is supported
    [Tags]    owasp    a02    tls
    ${response}=    Send GET Request    /api/v1/health
    ${tls_version}=    Get From Dictionary    ${response.headers}    X-TLS-Version    default=${EMPTY}
    Should Not Be Equal    ${tls_version}    TLSv1    msg=TLS 1.0 is enabled
    Should Not Be Equal    ${tls_version}    TLSv1.1    msg=TLS 1.1 is enabled
    Should Contain    ${tls_version}    TLSv1.2    ignore_case=True
    ...    msg=TLS version should be 1.2 or higher

Hardcoded Secrets Scan
    [Documentation]    A02:3 - Scan source for hardcoded secrets and API keys
    [Tags]    owasp    a02    secrets
    ${patterns}=    Create List    (?i)(api[_-]?key|secret|password|token)\\s*[=:]\\s*['\"][^'\"]{8,}['\"]
    ...    (?i)aws[_-]?(access[_-]?key|secret[_-]?key)\\s*[=:]\\s*[A-Z0-9]{16,}
    ...    (?i)(private[_-]?key)\\s*[=:]\\s*['\"]-----BEGIN
    ${src_dir}=    Set Variable    ${CURDIR}/../../../../src
    FOR    ${pattern}    IN    @{patterns}
        ${result}=    Run Process    rg    -i    --glob=!*.pyc    --glob=!*.min.js
        ...    ${pattern}    ${src_dir}    shell=${True}
        Should Be Empty    ${result.stdout}    msg=Potential hardcoded secret found: ${pattern}
    END

Sensitive Data In Transit
    [Documentation]    A02:4 - Verify sensitive data is encrypted in transit
    [Tags]    owasp    a02    transit
    ${response}=    Send GET Request    /api/v1/health
    Verify Encryption In Transit    ${BASE_URL}
    ${headers}=    Create Auth Headers
    ${response}=    Send POST Request    /api/v1/auth/login    body=${None}    headers=${headers}
    Should Not Contain    ${response.text}    password    msg=Password transmitted in plain text

Cookie Security Flags
    [Documentation]    A02:5 - Verify security flags on cookies
    [Tags]    owasp    a02    cookies
    ${body}=    Create Dictionary    email=test@test.com    password=testpass123
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    Check Cookie Security    ${response}

Password Storage Verification
    [Documentation]    A02:6 - Verify passwords are properly hashed in storage
    [Tags]    owasp    a02    password_storage
    ${user}=    Generate Test User
    ${headers}=    Create Auth Headers    ${user.token}
    ${response}=    Send GET Request    /api/v1/users/${user.user_id}    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${password_fields}=    Get Dictionary Values    ${json}    default=${EMPTY}
    FOR    ${value}    IN    @{password_fields}
        Should Not Match    ${value}    ${user.password}    msg=Password stored in plain text
    END

Key Strength Validation
    [Documentation]    A02:7 - Verify cryptographic key strength meets minimum requirements
    [Tags]    owasp    a02    key_strength
    ${response}=    Send GET Request    /api/v1/health
    ${json}=    Extract Response JSON    ${response}
    ${key_info}=    Get From Dictionary    ${json}    encryption    default=${None}
    IF    ${key_info} is not None
        ${key_size}=    Get From Dictionary    ${key_info}    key_size    default=${0}
        Should Be True    ${key_size} >= 256    msg=RSA key should be at least 2048 bits
    END

HTTPS Required For All Endpoints
    [Documentation]    A02:8 - Verify HTTP redirects to HTTPS
    [Tags]    owasp    a02    https
    ${http_url}=    Set Variable    http://api.adult-platform.local/api/v1/health
    ${response}=    Send GET Request    /api/v1/health
    ${url}=    Set Variable    ${response.url}
    Should Start With    ${url}    https://    msg=HTTP request not redirected to HTTPS

Sensitive Data Not In URL
    [Documentation]    A02:9 - Verify sensitive data is not passed in URLs
    [Tags]    owasp    a02    url_params
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/users?password=test123    headers=${headers}
    ${request_url}=    Set Variable    ${response.url}
    Should Not Contain    ${request_url}    password    msg=Password found in URL
    Should Not Contain    ${request_url}    token    msg=Token found in URL
    Should Not Contain    ${request_url}    secret    msg=Secret found in URL

*** Keywords ***
Setup Crypto Test Environment
    Setup Test Environment
