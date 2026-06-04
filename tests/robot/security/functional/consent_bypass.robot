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
Force Consent Via API
    [Documentation]    Test bypass of consent requirements via API manipulation
    [Tags]    functional    consent    bypass
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    consent_type=terms_of_service    consented=${True}    consent_version=999.0
    ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Consent granted with non-existent version
    ${body}=    Create Dictionary    consent_type=privacy_policy    consented=${True}
    ...    consent_timestamp=2020-01-01T00:00:00Z
    ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Consent granted with manipulated timestamp

Consent Withdrawal Race Condition
    [Documentation]    Test race condition in consent withdrawal
    [Tags]    functional    consent    race_condition
    ${headers}=    Create Auth Headers
    ${responses}=    Create List
    FOR    ${i}    IN RANGE    10
        ${body}=    Create Dictionary    consent_type=marketing    consented=${False}
        ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
        Append To List    ${responses}    ${response}
    END
    FOR    ${resp}    IN    @{responses}
        Should Not Contain    ${resp.text}    error
        ...    msg=Consent withdrawal race condition caused error
    END
    ${response}=    Send GET Request    /api/v1/consent    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${marketing}=    Get From Dictionary    ${json}    marketing    default=${True}
    Should Not Be True    ${marketing}    msg=Consent still active after withdrawal attempts

Consent Version Manipulation
    [Documentation]    Test manipulation of consent version to bypass updates
    [Tags]    functional    consent    version_manipulation
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    consent_type=terms_of_service    consented=${True}    consent_version=1.0
    ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Consent granted with outdated version
    ${response}=    Send GET Request    /api/v1/consent/status    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${current_version}=    Get From Dictionary    ${json}    current_version    default=${EMPTY}
    ${consented_version}=    Get From Dictionary    ${json}    consented_version    default=${EMPTY}
    Should Not Be Equal    ${consented_version}    ${current_version}
    ...    msg=Outdated consent version accepted without requiring re-consent

Consent Not Retrospectively Applied
    [Documentation]    Test that new consent terms are not retrospectively applied
    [Tags]    functional    consent    retrospective
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/consent    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${consented_at}=    Get From Dictionary    ${json}    consented_at    default=${EMPTY}
    Should Not Be Empty    ${consented_at}    msg=Consent timestamp missing
    ${body}=    Create Dictionary    consent_type=terms_of_service    consented=${True}
    ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
    ${new_response}=    Send GET Request    /api/v1/consent    headers=${headers}
    ${new_json}=    Extract Response JSON    ${new_response}
    ${new_consented_at}=    Get From Dictionary    ${new_json}    consented_at    default=${EMPTY}
    Should Be Equal    ${consented_at}    ${new_consented_at}
    ...    msg=Consent timestamp changed without new consent version

Minor Cannot Consent To Adult Content
    [Documentation]    Test that minors cannot consent to adult content
    [Tags]    functional    consent    age_restriction
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    birth_date=2010-01-01    consent_type=adult_content    consented=${True}
    ${response}=    Send POST Request    /api/v1/consent    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Minor consented to adult content
