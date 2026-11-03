import json
import os
import tempfile
import unittest
from unittest import mock

import raccoon_daily
import raccoon_login


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class ClientHeaderTests(unittest.TestCase):
    def test_personal_credentials_do_not_send_org_header(self):
        headers = raccoon_daily.desktop_headers(
            "token", {"office_identity": "personal"})

        self.assertNotIn("X-Org-Code", headers)
        self.assertEqual(headers["X-Client-Name"], "raccoon-work")
        self.assertEqual(headers["X-Client-Platform"], "desktop-windows")
        self.assertEqual(headers["X-Client-Version"], "v1.1.5")

    def test_organization_credentials_send_org_header(self):
        headers = raccoon_daily.desktop_headers(
            "token", {"officeIdentity": "ORG-TEST"})

        self.assertEqual(headers["X-Org-Code"], "ORG-TEST")

    def test_empty_and_non_string_org_fields_are_omitted(self):
        cases = (
            {},
            {"office_identity": ""},
            {"office_identity": "   "},
            {"office_identity": None},
            {"office_identity": ["ORG-TEST"]},
        )
        for credentials in cases:
            with self.subTest(credentials=credentials):
                headers = raccoon_daily.desktop_headers("token", credentials)
                self.assertNotIn("X-Org-Code", headers)

    def test_malformed_org_fields_are_rejected_before_request(self):
        cases = (
            {"office_identity": "ORG-\u4e2d\u6587"},
            {"office_identity": "ORG\nINJECTION"},
            {"office_identity": "ORG\x7fVALUE"},
        )
        for credentials in cases:
            with self.subTest(credentials=credentials):
                with mock.patch.object(raccoon_daily, "request") as request:
                    with self.assertRaises(ValueError):
                        raccoon_daily.trigger_daily("token", credentials)
                    request.assert_not_called()

    def test_login_client_uses_the_same_identity_headers(self):
        personal = raccoon_login.api_headers()
        organization = raccoon_login.api_headers(
            credentials={"officeIdentity": "ORG-TEST"})

        self.assertEqual(personal["X-Client-Name"], "raccoon-work")
        self.assertEqual(personal["X-Client-Version"], "v1.1.5")
        self.assertNotIn("X-Org-Code", personal)
        self.assertEqual(organization["X-Org-Code"], "ORG-TEST")

    def test_account_parser_uses_only_explicit_org_field(self):
        accounts = raccoon_daily.parse_accounts(
            "ORG-IN-NOTE|token||ORG-FROM-CREDENTIAL")

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["refresh"], "")
        self.assertEqual(accounts[0]["office_identity"], "ORG-FROM-CREDENTIAL")
        headers = raccoon_daily.desktop_headers(
            accounts[0]["token"], accounts[0])
        self.assertEqual(headers["X-Org-Code"], "ORG-FROM-CREDENTIAL")

    def test_legacy_personal_account_line_keeps_working(self):
        accounts = raccoon_daily.parse_accounts("note|token|refresh")

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["office_identity"], "")
        headers = raccoon_daily.desktop_headers(
            accounts[0]["token"], accounts[0])
        self.assertNotIn("X-Org-Code", headers)

    def test_auth_file_org_identity_is_carried_as_explicit_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            auth_file = os.path.join(folder, "auth.json")
            with open(auth_file, "w", encoding="utf-8") as handle:
                json.dump({
                    "access_token": "opaque-test-token",
                    "refresh_token": "opaque-test-refresh",
                    "office_identity": "ORG-AUTH",
                    "org_code": "IGNORED-DECOY",
                }, handle)

            credentials = raccoon_login.login_from_auth_file(auth_file)

        self.assertEqual(credentials["office_identity"], "ORG-AUTH")
        headers = raccoon_login.api_headers(
            credentials["token"], credentials)
        self.assertEqual(headers["X-Org-Code"], "ORG-AUTH")

    def test_auth_file_personal_identity_omits_org_header(self):
        with tempfile.TemporaryDirectory() as folder:
            auth_file = os.path.join(folder, "auth.json")
            with open(auth_file, "w", encoding="utf-8") as handle:
                json.dump({
                    "access_token": "opaque-test-token",
                    "office_identity": "personal",
                }, handle)

            credentials = raccoon_login.login_from_auth_file(auth_file)

        headers = raccoon_login.api_headers(
            credentials["token"], credentials)
        self.assertNotIn("X-Org-Code", headers)

    def test_authorization_exchange_keeps_org_identity(self):
        response = FakeResponse({
            "code": 0,
            "data": {
                "access_token": "opaque-test-token",
                "refresh_token": "opaque-test-refresh",
                "office_identity": "ORG-EXCHANGE",
            },
        })
        with mock.patch.object(
                raccoon_login, "request", return_value=response):
            credentials = raccoon_login.exchange_code("AUTH-CODE")

        self.assertEqual(credentials["office_identity"], "ORG-EXCHANGE")
        headers = raccoon_login.api_headers(
            credentials["token"], credentials)
        self.assertEqual(headers["X-Org-Code"], "ORG-EXCHANGE")

    def test_qr_success_response_keeps_org_identity(self):
        response = FakeResponse({
            "code": 0,
            "data": {
                "status": "success",
                "access_token": "opaque-test-token",
                "refresh_token": "opaque-test-refresh",
                "office_identity": "ORG-QR",
            },
        })
        with mock.patch.object(
                raccoon_login, "request", return_value=response):
            state = raccoon_login.poll_qr("QR-CODE")

        self.assertEqual(state["office_identity"], "ORG-QR")


class OnboardingRegressionTests(unittest.TestCase):
    def test_first_computer_and_mobile_rewards_are_claimed_once(self):
        account = {"token": "opaque-test-token", "office_identity": ""}
        with tempfile.TemporaryDirectory() as folder:
            state_file = os.path.join(folder, "onboarding.json")
            with mock.patch.dict(
                    os.environ, {"RACCOON_STATE_FILE": state_file}, clear=False):
                with mock.patch.object(
                        raccoon_daily,
                        "grant_login_points",
                        return_value={"granted": True,
                                      "popup": {"points": 3000}},
                ) as grant:
                    first = raccoon_daily.claim_onboarding(account)
                    second = raccoon_daily.claim_onboarding(account)

            self.assertEqual(grant.call_count, 2)
            self.assertEqual(
                [call.kwargs["mobile"] for call in grant.call_args_list],
                [False, True],
            )
            self.assertEqual(first, [
                "首次电脑端登录奖励 +3000",
                "首次手机端登录奖励 +3000",
            ])
            self.assertEqual(second, [])

            with open(state_file, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            ledger = next(iter(state["accounts"].values()))
            self.assertGreater(ledger["desktop_login_grant"], 0)
            self.assertGreater(ledger["mobile_login_grant"], 0)

    def test_already_granted_responses_also_settle_the_ledger(self):
        account = {"token": "opaque-test-token", "office_identity": ""}
        with tempfile.TemporaryDirectory() as folder:
            state_file = os.path.join(folder, "onboarding.json")
            with mock.patch.dict(
                    os.environ, {"RACCOON_STATE_FILE": state_file}, clear=False):
                with mock.patch.object(
                        raccoon_daily,
                        "grant_login_points",
                        return_value={"granted": False},
                ) as grant:
                    raccoon_daily.claim_onboarding(account)
                    raccoon_daily.claim_onboarding(account)

            self.assertEqual(grant.call_count, 2)


if __name__ == "__main__":
    unittest.main()
