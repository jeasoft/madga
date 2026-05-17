"""Instagram publisher — via Facebook Graph API.

Instagram doesn't have its own standalone OAuth flow; you go through
Facebook Login and pick a connected Instagram Business Account. The
constraint that makes this gnarlier than X/LinkedIn:

  - The IG account MUST be a Business (or Creator) account
  - It MUST be linked to a Facebook Page you admin
  - Posts MUST have media (image or video) — no text-only posts
  - The media URL MUST be publicly fetchable by Meta's servers
    (localhost won't work — use ngrok in dev, a real domain in prod)

Setup on developers.facebook.com:
    1. Create app → type "Business"
    2. Add product "Facebook Login for Business" + "Instagram Graph API"
    3. Settings → OAuth: add redirect URL
    4. Permissions/scopes:
         instagram_basic
         instagram_content_publish
         pages_show_list
         pages_read_engagement
         business_management
    5. App in Live mode for non-test users (Dev mode works for the
       app owner's IG)

After OAuth we resolve:
    - Long-lived user access token (exchanged from short-lived)
    - The Facebook Pages the user admins
    - For each Page, the connected Instagram Business Account
    - Pick the first one (or surface a picker — TODO 0.3.9)

Publishing is a two-step dance:
    Step 1: POST {ig-user-id}/media with image_url + caption
            → returns creation_id (a media container)
    Step 2: POST {ig-user-id}/media_publish with creation_id
            → returns the published media id
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from django.utils.translation import gettext_lazy as _

from .base import CredField, register_publisher
from .social import _AccountPublisher, _http_post_form, _http_post_json


logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
FB_AUTH = "https://www.facebook.com/v21.0/dialog/oauth"


@register_publisher
class InstagramOAuthPublisher(_AccountPublisher):
    key = "instagram"
    label = _("Instagram")
    description = _(
        "Post to an Instagram Business account via Facebook Graph. "
        "Posts must include an image — no text-only posts."
    )
    icon = "image"
    char_limit = 2200

    oauth_supported = True
    oauth_scopes = [
        "instagram_basic",
        "instagram_content_publish",
        "pages_show_list",
        "pages_read_engagement",
        "business_management",
    ]
    credential_fields: list[CredField] = []

    setup_console_url = "https://developers.facebook.com/apps/"
    setup_instructions = [
        {
            "title": "Connect your Instagram to a Facebook Page",
            "body": (
                "Instagram only allows posting via the Graph API on Business "
                "or Creator accounts that are linked to a Facebook Page. "
                "On Instagram → Settings → Account → Switch to Professional Account, "
                "then connect the Page in the same flow. Without this, the "
                "rest of the setup won't surface any IG account."
            ),
            "url": "https://help.instagram.com/502981923235522",
        },
        {
            "title": "Create a Facebook App",
            "body": (
                "developers.facebook.com → My Apps → Create App. "
                "Pick type 'Business'. Name it whatever you'll use to "
                "post (e.g. 'aplica.do publisher')."
            ),
            "url": "https://developers.facebook.com/apps/",
        },
        {
            "title": "Add Instagram Graph API + Facebook Login products",
            "body": (
                "In your app → Add Products: 'Instagram Graph API' and "
                "'Facebook Login for Business'. Both are needed."
            ),
            "url": "",
        },
        {
            "title": "Configure OAuth redirect",
            "body": (
                "Facebook Login → Settings → Valid OAuth Redirect URIs.\n"
                "Add:\n<copy>{CALLBACK}</copy>\n"
                "Important: localhost works for testing but the IG image_url "
                "needs to be publicly reachable for the actual post call "
                "(use ngrok or deploy)."
            ),
            "url": "",
        },
        {
            "title": "App in Live mode (for non-developer users)",
            "body": (
                "Test mode lets the app admin post to their own IG. To let "
                "any user OAuth through your app, App Mode = Live and "
                "complete App Review for instagram_content_publish + "
                "pages_show_list."
            ),
            "url": "",
        },
        {
            "title": "Copy App ID + App Secret",
            "body": (
                "App Settings → Basic. Copy both.\n\n"
                "<copy>MADGA_OAUTH = {\n"
                "    'instagram': {\n"
                "        'client_id': 'APP_ID',\n"
                "        'client_secret': 'APP_SECRET',\n"
                "    },\n"
                "}</copy>"
            ),
            "url": "",
        },
    ]

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def oauth_authorize_url(self, redirect_uri: str, state: str, pkce_verifier: str) -> str:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['instagram']['client_id'] is not configured")
        client_id, _ = creds
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.oauth_scopes),
            "response_type": "code",
        }
        return f"{FB_AUTH}?{urllib.parse.urlencode(params)}"

    def oauth_exchange(self, code: str, redirect_uri: str, pkce_verifier: str) -> dict:
        creds = self.oauth_client_credentials()
        if not creds:
            raise RuntimeError("MADGA_OAUTH['instagram'] is not configured")
        client_id, client_secret = creds

        # 1) Short-lived user access token
        url = (
            f"{GRAPH}/oauth/access_token?"
            + urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            })
        )
        with urllib.request.urlopen(url, timeout=15) as resp:
            short = json.loads(resp.read().decode("utf-8"))
        short_token = short.get("access_token")
        if not short_token:
            raise RuntimeError(f"FB short-lived token exchange returned no access_token: {short}")

        # 2) Exchange for long-lived user token (~60 days)
        long_url = (
            f"{GRAPH}/oauth/access_token?"
            + urllib.parse.urlencode({
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "fb_exchange_token": short_token,
            })
        )
        with urllib.request.urlopen(long_url, timeout=15) as resp:
            longt = json.loads(resp.read().decode("utf-8"))
        user_token = longt.get("access_token") or short_token

        # 3) List the Pages the user admins
        pages_url = f"{GRAPH}/me/accounts?access_token={urllib.parse.quote(user_token)}"
        with urllib.request.urlopen(pages_url, timeout=15) as resp:
            pages = json.loads(resp.read().decode("utf-8")).get("data", []) or []
        if not pages:
            raise RuntimeError(
                "No Facebook Pages found on this account. Connect an Instagram "
                "Business account to a Page first."
            )

        # 4) For each Page, see if it has an IG Business Account.
        # We pick the first one with IG attached. (A future release may
        # surface a picker UI when there are multiple.)
        chosen_page = None
        ig_user_id = None
        ig_username = ""
        for page in pages:
            pid = page.get("id")
            page_token = page.get("access_token")
            if not pid or not page_token:
                continue
            detail_url = (
                f"{GRAPH}/{pid}?fields=instagram_business_account,name"
                f"&access_token={urllib.parse.quote(page_token)}"
            )
            try:
                with urllib.request.urlopen(detail_url, timeout=15) as resp:
                    detail = json.loads(resp.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                continue
            iba = (detail.get("instagram_business_account") or {}).get("id")
            if iba:
                chosen_page = {"id": pid, "name": detail.get("name", ""), "access_token": page_token}
                ig_user_id = iba
                # Fetch IG username for display
                try:
                    ig_url = f"{GRAPH}/{iba}?fields=username&access_token={urllib.parse.quote(page_token)}"
                    with urllib.request.urlopen(ig_url, timeout=15) as resp:
                        ig_data = json.loads(resp.read().decode("utf-8"))
                    ig_username = ig_data.get("username", "")
                except Exception:  # noqa: BLE001
                    pass
                break

        if not chosen_page or not ig_user_id:
            raise RuntimeError(
                "Your Facebook account has Pages but none have an Instagram "
                "Business account attached. Connect your IG to a Page first."
            )

        handle = f"@{ig_username}" if ig_username else f"ig:{ig_user_id}"
        return {
            "credentials": {
                "user_access_token": user_token,
                "page_access_token": chosen_page["access_token"],
                "page_id": chosen_page["id"],
                "page_name": chosen_page["name"],
                "ig_user_id": ig_user_id,
                "ig_username": ig_username,
            },
            "handle": handle,
            "display_name": ig_username or chosen_page["name"] or "Instagram",
        }

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def _resolve_image_url(self, job) -> str:
        """Pick a public, fetchable image URL for the post.

        Order of preference:
          1. job.related_post.featured_image (with absolute URL via site.domain)
          2. job.related_post.og_image
          3. nothing → IG publish fails with a clear message
        """
        post = getattr(job, "related_post", None)
        if not post:
            return ""

        media = getattr(post, "featured_image", None) or getattr(post, "og_image", None)
        if not media or not media.file:
            return ""

        url = media.file.url
        if url.startswith("http"):
            return url

        # Make absolute using the site's domain
        site = getattr(job, "site", None)
        domain = (getattr(site, "domain", "") or "").strip()
        if domain and not domain.startswith("http"):
            scheme = "https" if domain != "localhost" else "http"
            url = f"{scheme}://{domain}{url}"
        return url

    def _publish_one(self, job, account) -> None:
        creds = account.get_credentials()
        ig_user_id = creds.get("ig_user_id")
        page_token = creds.get("page_access_token")
        if not ig_user_id or not page_token:
            raise RuntimeError("Instagram account is missing ig_user_id or page_access_token")

        image_url = self._resolve_image_url(job)
        if not image_url:
            raise RuntimeError(
                "Instagram requires an image. Set a Featured Image on the "
                "post before broadcasting."
            )
        if image_url.startswith("http://localhost") or "127.0.0.1" in image_url:
            raise RuntimeError(
                "Instagram fetches the image_url from Meta's servers; localhost "
                "URLs won't work. Use ngrok in dev, or test against a deployed site."
            )

        caption = job.body_text or self.default_copy(job)

        # Step 1: create the media container
        container = _http_post_form(
            f"{GRAPH}/{ig_user_id}/media",
            {
                "image_url": image_url,
                "caption": caption,
                "access_token": page_token,
            },
            headers={},
        )
        creation_id = container.get("id")
        if not creation_id:
            raise RuntimeError(f"IG create container returned no id: {container}")

        # Step 2: publish the container
        result = _http_post_form(
            f"{GRAPH}/{ig_user_id}/media_publish",
            {
                "creation_id": creation_id,
                "access_token": page_token,
            },
            headers={},
        )
        if not result.get("id"):
            raise RuntimeError(f"IG media_publish returned no id: {result}")

    def test_connection(self, account) -> tuple[bool, str]:
        creds = account.get_credentials()
        ig_user_id = creds.get("ig_user_id")
        page_token = creds.get("page_access_token")
        if not ig_user_id or not page_token:
            return False, "Missing ig_user_id or page_access_token. Reconnect the account."
        try:
            url = (
                f"{GRAPH}/{ig_user_id}?fields=username,followers_count"
                f"&access_token={urllib.parse.quote(page_token)}"
            )
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return True, (
                f"Authenticated as @{data.get('username', '?')} "
                f"({data.get('followers_count', '?')} followers)"
            )
        except Exception as e:  # noqa: BLE001
            return False, f"Instagram verify failed: {e}"
