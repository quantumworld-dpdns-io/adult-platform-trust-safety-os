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
Unauthorized Access - No Token
    [Documentation]    Test API access without any authentication
    [Tags]    api    authorization    unauthorized
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${protected_endpoints}=    Create List    /api/v1/users    /api/v1/admin/users
    ...    /api/v1/admin/settings    /api/v1/payments    /api/v1/consent
    FOR    ${endpoint}    IN    @{protected_endpoints}
        ${response}=    Send GET Request    ${endpoint}    headers=${headers}
        Response Status Should Be    ${response}    401
    END

Role Bypass - User To Admin
    [Documentation]    Test role-based access control bypass
    [Tags]    api    authorization    role_bypass
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    role=admin
    ${response}=    Send POST Request    /api/v1/users/role
    ...    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Role escalation accepted via API
    ${body}=    Create Dictionary    permissions=["admin:read", "admin:write"]
    ${response}=    Send PUT Request    /api/v1/users/me/permissions
    ...    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Permission modification accepted

Token Scope Violation
    [Documentation]    Test accessing resources outside token scope
    [Tags]    api    authorization    scope_violation
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/users    headers=${headers}
    Response Status Should Be    ${response}    403
    ${response}=    Send GET Request    /api/v1/admin/settings    headers=${headers}
    Response Status Should Be    ${response}    403
    ${body}=    Create Dictionary    user_id=other_user_id
    ${response}=    Send DELETE Request    /api/v1/users/other_user_id    headers=${headers}
    Response Status Should Be    ${response}    403

Cross-Tenant Access
    [Documentation]    Test accessing resources from another tenant
    [Tags]    api    authorization    cross_tenant
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/tenants/other_tenant/users    headers=${headers}
    Response Status Should Be    ${response}    403
    ${response}=    Send GET Request    /api/v1/tenants/other_tenant/data    headers=${headers}
    Response Status Should Be    ${response}    403
    ${body}=    Create Dictionary    tenant_id=other_tenant
    ${response}=    Send POST Request    /api/v1/data    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Cross-tenant data access accepted

Horizontal Privilege Escalation
    [Documentation]    Test accessing other users' resources
    [Tags]    api    authorization    horizontal
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/users/other_user_id/profile    headers=${headers}
    Response Status Should Be    ${response}    403
    ${response}=    Send GET Request    /api/v1/users/other_user_id/payments    headers=${headers}
    Response Status Should Be    ${response}    403
    ${body}=    Create Dictionary    data=sensitive_data
    ${response}=    Send POST Request    /api/v1/users/other_user_id/data
    ...    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Horizontal privilege escalation succeeded

Vertical Privilege Escalation
    [Documentation]    Test accessing admin resources as regular user
    [Tags]    api    authorization    vertical
    ${headers}=    Create Auth Headers
    ${admin_endpoints}=    Create List    /api/v1/admin/users    /api/v1/admin/settings
    ...    /api/v1/admin/logs    /api/v1/admin/audit-trail
    FOR    ${endpoint}    IN    @{admin_endpoints}
        ${response}=    Send GET Request    ${endpoint}    headers=${headers}
        Response Status Should Be    ${response}    403
    END

HTTP Method Tampering
    [Documentation]    Test access control bypass via HTTP method tampering
    [Tags]    api    authorization    method_tampering
    ${headers}=    Create Auth Headers
    ${methods}=    Create List    GET    POST    PUT    DELETE    PATCH
    FOR    ${method}    IN    @{methods}
        ${response}=    Send Request    api    ${method}    /api/v1/admin/users
        ...    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Admin endpoint accessible via ${method}
    END

Mass Assignment
    [Documentation]    Test for mass assignment vulnerability
    [Tags]    api    authorization    mass_assignment
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    email=user@test.com    role=admin    is_admin=${True}
    ...    permissions=["admin:read","admin:write"]
    ${response}=    Send PUT Request    /api/v1/users/me    body=${body}    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${role}=    Get From Dictionary    ${json}    role    default=${EMPTY}
    Should Not Be Equal    ${role}    admin    msg=Mass assignment allowed role change
