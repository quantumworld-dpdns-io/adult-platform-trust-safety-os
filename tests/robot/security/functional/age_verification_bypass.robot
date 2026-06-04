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
Direct API Age Claim Bypass
    [Documentation]    Test bypass of age verification via direct API manipulation
    [Tags]    functional    age_verification    bypass
    ${body}=    Create Dictionary    birth_date=2000-01-01    age_verified=${True}
    ${response}=    Send POST Request    /api/v1/users/profile    body=${body}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Age verification bypassed via direct API manipulation
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    age=25    age_verified=true
    ${response}=    Send PUT Request    /api/v1/users/me/age-verification    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Age verification status manipulated via API

Document Forgery Detection
    [Documentation]    Test detection of forged age verification documents
    [Tags]    functional    age_verification    document_forgery
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    document_type=id_card    document_number=FAKE12345
    ...    expiry_date=2030-12-31
    ${response}=    Send POST Request    /api/v1/verification/documents    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Forged document accepted
    ${body}=    Create Dictionary    document_type=drivers_license    image_url=http://fake-docs.example.com/id.jpg
    ${response}=    Send POST Request    /api/v1/verification/documents    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Forged document image accepted

Liveness Bypass Attempt
    [Documentation]    Test bypass of liveness detection for age verification
    [Tags]    functional    age_verification    liveness
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    liveness_token=bypass    face_data=null
    ${response}=    Send POST Request    /api/v1/verification/liveness    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Liveness detection bypassed
    ${body}=    Create Dictionary    photo_url=http://fake-photos.example.com/face.jpg    liveness=passed
    ${response}=    Send POST Request    /api/v1/verification/liveness    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Liveness bypassed with static photo

Session Age Manipulation
    [Documentation]    Test manipulation of age verification in session
    [Tags]    functional    age_verification    session
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${body}=    Create Dictionary    age_verified=${True}    verification_level=full
    ${response}=    Send PUT Request    /api/v1/users/me    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Age verification status modified in session
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${age_verified}=    Get From Dictionary    ${json}    age_verified    default=${False}
    Should Not Be True    ${age_verified}    msg=Age verification persisted after manipulation

Age Verification Expiry Check
    [Documentation]    Test that age verification expires and requires re-verification
    [Tags]    functional    age_verification    expiry
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/users/me/verification    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${expires_at}=    Get From Dictionary    ${json}    expires_at    default=${EMPTY}
    Should Not Be Empty    ${expires_at}    msg=Age verification has no expiry date
