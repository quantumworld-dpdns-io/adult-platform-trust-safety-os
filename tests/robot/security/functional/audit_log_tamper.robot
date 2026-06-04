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
Chain Integrity Check
    [Documentation]    Test audit log chain integrity verification
    [Tags]    functional    audit_tamper    chain_integrity
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/audit-log/chain-integrity    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    Dictionary Should Contain Key    ${json}    chain_valid    msg=Chain integrity check not available
    Should Be True    ${json}[chain_valid]    msg=Audit log chain integrity compromised
    ${response}=    Send POST Request    /api/v1/admin/audit-log/verify-chain
    ...    body=${None}    headers=${admin_headers}
    Response Status Should Be    ${response}    200

Hash Verification
    [Documentation]    Test audit log hash verification
    [Tags]    functional    audit_tamper    hash
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/audit-log/entries?limit=10    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    ${entries}=    Get From Dictionary    ${json}    entries    default=${EMPTY}
    FOR    ${entry}    IN    @{entries}
        Dictionary Should Contain Key    ${entry}    hash    msg=Audit log entry missing hash
        Dictionary Should Contain Key    ${entry}    previous_hash    msg=Audit log entry missing previous_hash
    END

Timestamp Manipulation
    [Documentation]    Test detection of timestamp manipulation in audit logs
    [Tags]    functional    audit_tamper    timestamp
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    timestamp=2020-01-01T00:00:00Z    action=test_action
    ${response}=    Send POST Request    /api/v1/audit-log    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Audit log entry accepted with past timestamp
    ${body}=    Create Dictionary    timestamp=2099-12-31T23:59:59Z    action=test_action
    ${response}=    Send POST Request    /api/v1/audit-log    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Audit log entry accepted with future timestamp

Log Deletion Detection
    [Documentation]    Test detection of audit log deletion attempts
    [Tags]    functional    audit_tamper    deletion
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send DELETE Request    /api/v1/admin/audit-log/entries    headers=${admin_headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Audit log deletion endpoint accessible
    ${response}=    Send DELETE Request    /api/v1/admin/audit-log    headers=${admin_headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Audit log bulk deletion accessible
    ${body}=    Create Dictionary    entry_id=123
    ${response}=    Send DELETE Request    /api/v1/admin/audit-log/entries/123    headers=${admin_headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Individual audit log deletion accessible

Audit Log Immutability
    [Documentation]    Test that audit logs cannot be modified after creation
    [Tags]    functional    audit_tamper    immutability
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    action=test_action    details=test
    ${response}=    Send POST Request    /api/v1/audit-log    body=${body}    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${entry_id}=    Get From Dictionary    ${json}    id    default=${EMPTY}
    IF    "${entry_id}" != "${EMPTY}"
        ${put_body}=    Create Dictionary    action=modified_action
        ${response}=    Send PUT Request    /api/v1/audit-log/${entry_id}
        ...    body=${put_body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Audit log entry modification accepted
    END

Audit Trail Gap Detection
    [Documentation]    Test detection of gaps in audit trail
    [Tags]    functional    audit_tamper    gaps
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/audit-log/gaps    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    ${gaps}=    Get From Dictionary    ${json}    gaps    default=${EMPTY}
    Should Be Empty    ${gaps}    msg=Gaps detected in audit trail
