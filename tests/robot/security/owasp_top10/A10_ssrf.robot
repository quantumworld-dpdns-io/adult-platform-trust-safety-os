*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    JSON
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    30s

*** Test Cases ***
URL Parameter SSRF
    [Documentation]    A10:1 - Test SSRF via URL parameter
    [Tags]    owasp    a10    ssrf    url
    ${payloads}=    SSRF Payloads
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=${payload}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=SSRF accepted with URL parameter: ${payload}
    END

Webhook SSRF
    [Documentation]    A10:2 - Test SSRF via webhook configuration
    [Tags]    owasp    a10    ssrf    webhook
    ${payloads}=    SSRF Payloads
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    callback_url=${payload}    event=test
        ${response}=    Send POST Request    /api/v1/webhooks    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=SSRF accepted via webhook: ${payload}
    END

Internal Service Discovery
    [Documentation]    A10:3 - Test for internal service discovery via SSRF
    [Tags]    owasp    a10    ssrf    internal
    ${internal_urls}=    Create List    http://127.0.0.1:8080    http://127.0.0.1:3000
    ...    http://127.0.0.1:5432    http://127.0.0.1:6379    http://127.0.0.1:27017
    FOR    ${url}    IN    @{internal_urls}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=${url}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Internal service accessible via SSRF: ${url}
    END

DNS Rebinding Attack
    [Documentation]    A10:4 - Test for DNS rebinding vulnerabilities
    [Tags]    owasp    a10    ssrf    dns_rebinding
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    url=http://127.0.0.1.nip.io
    ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=DNS rebinding attack may have succeeded

Port Scanning Via SSRF
    [Documentation]    A10:5 - Test for port scanning via SSRF
    [Tags]    owasp    a10    ssrf    port_scan
    ${ports}=    Create List    22    80    443    3306    5432    6379    8080    8443
    FOR    ${port}    IN    @{ports}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=http://127.0.0.1:${port}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Port ${port} accessible via SSRF
    END

File Protocol Access
    [Documentation]    A10:6 - Test for file:// protocol access via SSRF
    [Tags]    owasp    a10    ssrf    file_protocol
    ${file_payloads}=    Create List    file:///etc/passwd    file:///etc/shadow
    ...    file:///proc/self/environ    file:///proc/self/cmdline
    FOR    ${payload}    IN    @{file_payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=${payload}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=File protocol accessible via SSRF: ${payload}
    END

Cloud Metadata Access
    [Documentation]    A10:7 - Test for cloud metadata endpoint access
    [Tags]    owasp    a10    ssrf    cloud_metadata
    ${metadata_urls}=    Create List
    ...    http://169.254.169.254/latest/meta-data/
    ...    http://169.254.169.254/latest/meta-data/iam/security-credentials/
    ...    http://metadata.google.internal/
    ...    http://169.254.169.254/metadata/instance?api-version=2021-02-01
    FOR    ${url}    IN    @{metadata_urls}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=${url}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Cloud metadata accessible via SSRF: ${url}
    END

SSRF With IP Encoding Bypass
    [Documentation]    A10:8 - Test SSRF with IP encoding bypass attempts
    [Tags]    owasp    a10    ssrf    encoding_bypass
    ${encoded_urls}=    Create List
    ...    http://0x7f000001
    ...    http://0177.0.0.1
    ...    http://2130706433
    ...    http://0x7f.0x00.0x00.0x01
    FOR    ${url}    IN    @{encoded_urls}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    url=${url}
        ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=SSRF with IP encoding bypass succeeded: ${url}
    END

SSRF With Redirect Bypass
    [Documentation]    A10:9 - Test SSRF with redirect bypass
    [Tags]    owasp    a10    ssrf    redirect
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    url=http://httpbin.org/redirect-to?url=http://169.254.169.254/latest/meta-data/
    ${response}=    Send POST Request    /api/v1/fetch    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=SSRF with redirect bypass succeeded
