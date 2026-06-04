*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    JSON
Library    OperatingSystem
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    30s

*** Test Cases ***
Deserialization Attack - Java
    [Documentation]    A08:1 - Test for unsafe deserialization vulnerabilities
    [Tags]    owasp    a08    deserialization
    ${malicious_payload}=    Evaluate    __import__('base64').b64encode(b'\x00\x00\x00\x00\x00\x00\x00\x00').decode()
    ${headers}=    Create Auth Headers
    ${response}=    Send POST Request    /api/v1/import
    ...    body=${malicious_payload}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Deserialization attack may have succeeded
    Should Not Contain    ${response.text}    Exception    msg=Exception details exposed

Deserialization Attack - Python Pickle
    [Documentation]    A08:2 - Test for Python pickle deserialization
    [Tags]    owasp    a08    deserialization    pickle
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    format=pickle    data=eyJfc3RhdGVzIjoge319
    ${response}=    Send POST Request    /api/v1/data/import    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Pickle deserialization endpoint accessible

CI/CD Pipeline Integrity
    [Documentation]    A08:3 - Verify CI/CD pipeline integrity controls
    [Tags]    owasp    a08    cicd
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/.github/workflows/*.yml
    ...    msg=No CI/CD workflow files found
    ${result}=    Run Process    grep    -r    "pull_request_target"    ${project_root}/.github/
    ...    shell=${True}
    Should Be Empty    ${result.stdout}    msg=pull_request_target used - potential privilege escalation
    ${result}=    Run Process    grep    -r    "permissions:"    ${project_root}/.github/workflows/
    ...    shell=${True}
    Should Not Be Empty    ${result.stdout}    msg=No permissions block in CI/CD workflows

Software Supply Chain Verification
    [Documentation]    A08:4 - Verify software supply chain integrity
    [Tags]    owasp    a08    supply_chain
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/.npmrc    msg=.npmrc missing for supply chain security
    ${result}=    Run Process    cat    ${project_root}/.npmrc    shell=${True}
    Should Contain    ${result.stdout}    audit=true    msg=npm audit not enabled
    File Should Exist    ${project_root}/requirements.txt    msg=requirements.txt missing
    File Should Exist    ${project_root}/requirements.lock    msg=requirements.lock missing

Update Mechanism Integrity
    [Documentation]    A08:5 - Verify update mechanism uses signed packages
    [Tags]    owasp    a08    update_integrity
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/package.json    msg=package.json missing
    ${result}=    Run Process    grep    -c    "integrity"    ${project_root}/package-lock.json
    ...    shell=${True}
    Should Not Be Equal    ${result.stdout}    0    msg=Package integrity checks not present

Unsigned Updates Detection
    [Documentation]    A08:6 - Detect unsigned update mechanisms
    [Tags]    owasp    a08    unsigned_updates
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    ${result}=    Run Process    grep    -r    "auto_update"    ${project_root}/src/
    ...    shell=${True}
    Should Be Empty    ${result.stdout}    msg=Unsigned auto-update mechanism detected

Subresource Integrity Check
    [Documentation]    A08:7 - Verify subresource integrity for external resources
    [Tags]    owasp    a08    sri
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    ${result}=    Run Process    rg    -i    '<script.*src="http'    ${project_root}/
    ...    --glob='*.html'    --glob='*.js'    shell=${True}
    Should Be Empty    ${result.stdout}    msg=External scripts without SRI found
    ${result}=    Run Process    rg    -i    '<link.*href="http'    ${project_root}/
    ...    --glob='*.html'    shell=${True}
    Should Be Empty    ${result.stdout}    msg=External stylesheets without SRI found

Artifact Signing Verification
    [Documentation]    A08:8 - Verify build artifacts are signed
    [Tags]    owasp    a08    artifact_signing
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/.github/workflows/release.yml
    ...    msg=No release workflow found for artifact signing

Dependency Lock File Integrity
    [Documentation]    A08:9 - Verify dependency lock files are not tampered
    [Tags]    owasp    a08    lock_integrity
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/package-lock.json    msg=package-lock.json missing
    File Should Exist    ${project_root}/yarn.lock    msg=yarn.lock missing
    ${result}=    Run Process    git    diff    --name-only    ${project_root}/package-lock.json
    ...    shell=${True}    cwd=${project_root}
    Should Be Empty    ${result.stdout}    msg=package-lock.json has uncommitted changes

Webhook Payload Validation
    [Documentation]    A08:10 - Verify webhook payloads are validated
    [Tags]    owasp    a08    webhook
    ${headers}=    Create Dictionary    Content-Type=application/json    X-Hub-Signature-256=invalid
    ${body}=    Create Dictionary    event=test    data={}
    ${response}=    Send POST Request    /api/v1/webhooks    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Webhook accepted with invalid signature
