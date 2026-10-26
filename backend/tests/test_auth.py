def test_register_and_login(client):
    # 1. Register new user
    reg_response = client.post(
        "/auth/register",
        json={
            "email": "alex.chen@example.com",
            "password": "SecretPassword123!",
            "full_name": "Alex Chen"
        }
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["email"] == "alex.chen@example.com"
    assert reg_data["full_name"] == "Alex Chen"
    token = reg_data["access_token"]

    # 2. Duplicate registration should fail
    dup_response = client.post(
        "/auth/register",
        json={
            "email": "alex.chen@example.com",
            "password": "AnotherPassword!",
            "full_name": "Alex Chen Duplicate"
        }
    )
    assert dup_response.status_code == 400

    # 3. Login with correct credentials
    login_response = client.post(
        "/auth/login",
        json={
            "email": "alex.chen@example.com",
            "password": "SecretPassword123!"
        }
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data

    # 4. Login with invalid password
    bad_login = client.post(
        "/auth/login",
        json={
            "email": "alex.chen@example.com",
            "password": "WrongPassword!"
        }
    )
    assert bad_login.status_code == 401

    # 5. Protected route /auth/me with valid token
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "alex.chen@example.com"
    assert me_data["full_name"] == "Alex Chen"

    # 6. Protected route without token
    unauth_response = client.get("/auth/me")
    assert unauth_response.status_code == 401

    # 7. Logout endpoint
    logout_resp = client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
