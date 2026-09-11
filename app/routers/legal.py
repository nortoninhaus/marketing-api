"""
HTML endpoints for Privacy Policy, Terms of Service, and Public Landing Page.
Designed to meet strict Google OAuth Verification, YouTube API Services Terms of Service,
and Google API Services User Data Policy requirements.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Legal & Compliance"])

COMMON_CSS = """
:root {
  --primary: #4f46e5;
  --primary-dark: #4338ca;
  --primary-light: #e0e7ff;
  --text-main: #0f172a;
  --text-muted: #475569;
  --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  --card-bg: #ffffff;
  --border: #e2e8f0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--text-main);
  background: var(--bg-gradient);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  padding: 1rem 2rem;
  position: sticky;
  top: 0;
  z-index: 50;
}
.nav-container {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.brand-title {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
}
.brand-badge {
  background: var(--primary-light);
  color: var(--primary-dark);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 9999px;
  text-transform: uppercase;
}
nav a {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.925rem;
  font-weight: 500;
  margin-left: 1.5rem;
  transition: color 0.15s ease;
}
nav a:hover, nav a.active {
  color: var(--primary);
}
main {
  max-width: 960px;
  margin: 2.5rem auto;
  padding: 0 1.5rem;
  flex: 1;
  width: 100%;
}
.doc-card {
  background: var(--card-bg);
  border-radius: 16px;
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.02);
  border: 1px solid var(--border);
  padding: 3rem;
}
h1 {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--text-main);
  margin-bottom: 0.5rem;
}
.effective-date {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 1rem;
}
h2 {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 2rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 2px solid var(--primary-light);
}
p, ul, ol {
  color: var(--text-muted);
  font-size: 0.975rem;
  margin-bottom: 1rem;
}
ul, ol {
  padding-left: 1.5rem;
}
li {
  margin-bottom: 0.5rem;
}
strong {
  color: var(--text-main);
}
.highlight-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-left: 4px solid #16a34a;
  border-radius: 8px;
  padding: 1.25rem;
  margin: 1.5rem 0;
}
.highlight-box h3 {
  color: #15803d;
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}
.highlight-box p {
  color: #166534;
  margin-bottom: 0;
  font-size: 0.925rem;
}
.alert-box {
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-left: 4px solid #d97706;
  border-radius: 8px;
  padding: 1.25rem;
  margin: 1.5rem 0;
}
.alert-box p {
  color: #92400e;
  margin-bottom: 0;
  font-size: 0.925rem;
}
footer {
  background: #ffffff;
  border-top: 1px solid var(--border);
  padding: 2rem 1.5rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-top: auto;
}
footer a {
  color: var(--primary);
  text-decoration: none;
  margin: 0 0.5rem;
}
footer a:hover {
  text-decoration: underline;
}
@media (max-width: 640px) {
  .doc-card { padding: 1.75rem; }
  h1 { font-size: 1.75rem; }
  header { padding: 1rem; }
}
"""

@router.get("/privacy", response_class=HTMLResponse)
@router.get("/privacy-policy", response_class=HTMLResponse)
@router.get("/api/v1/privacy", response_class=HTMLResponse)
async def privacy_policy():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Privacy Policy - INHAUS BRAIN</title>
  <meta name="description" content="Privacy Policy for INHAUS BRAIN and Inhaus Marketing API services.">
  <style>{COMMON_CSS}</style>
</head>
<body>
  <header>
    <div class="nav-container">
      <a href="/" class="brand-title">
        <span>⚡ INHAUS BRAIN</span>
        <span class="brand-badge">Platform</span>
      </a>
      <nav>
        <a href="/">About & Overview</a>
        <a href="/privacy" class="active">Privacy Policy</a>
        <a href="/terms">Terms of Service</a>
      </nav>
    </div>
  </header>

  <main>
    <div class="doc-card">
      <h1>Privacy Policy</h1>
      <div class="effective-date">Last Updated: September 10, 2026 | Effective Date: September 10, 2026</div>

      <p>
        Welcome to <strong>INHAUS BRAIN</strong> (operated by Inhaus Corp / Inhaus Marketing, "we", "us", or "our").
        We provide marketing analytics, campaign orchestration, unified reporting, and multi-platform data integration
        services through our web dashboard and API (collectively, the "Service").
      </p>

      <h2>1. Purpose of INHAUS BRAIN</h2>
      <p>
        INHAUS BRAIN enables businesses, agencies, and content creators to monitor and analyze their digital marketing
        performance across multiple ad networks and content platforms (including Google Ads, YouTube, Meta Ads, TikTok,
        and Google Analytics 4) within a single unified analytics dashboard.
      </p>

      <h2>2. Information We Access & Collect</h2>
      <p>When you connect third-party platforms to INHAUS BRAIN, we access only the data necessary to provide analytics:</p>
      <ul>
        <li><strong>Account Information:</strong> Basic profile identifiers (email address, account name, user ID) necessary for session authentication.</li>
        <li><strong>Advertising & Performance Metrics:</strong> Read-only aggregate campaign data including impressions, clicks, spend, conversions, reach, video views, watch time, and subscriber growth.</li>
        <li><strong>Channel & Asset Identifiers:</strong> Channel IDs, ad account IDs, campaign IDs, and video metadata to map analytics correctly to your dashboard.</li>
      </ul>

      <div class="highlight-box">
        <h3>Google User Data & YouTube API Services Compliance</h3>
        <p>
          <strong>INHAUS BRAIN</strong> accesses Google User Data and YouTube API Services. Our collection, use, and transfer of information
          received from Google APIs strictly adheres to the 
          <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">Google API Services User Data Policy</a>,
          including the <strong>Limited Use</strong> requirements.
        </p>
      </div>

      <h2>3. How We Use Google & YouTube Data</h2>
      <p>When you connect your Google Ads or YouTube account to INHAUS BRAIN:</p>
      <ul>
        <li>We access YouTube channels (including Brand Accounts managed by your profile) and YouTube Analytics solely to display performance dashboards (views, watch time, engagement, subscriber trends).</li>
        <li>We access Google Ads data solely to report on campaign metrics (spend, impressions, clicks, conversions, ROAS).</li>
        <li><strong>No Advertising or Resale:</strong> We NEVER sell your Google/YouTube user data, transfer it to third-party data brokers, or use it for serving advertisements.</li>
        <li><strong>No AI Model Training:</strong> Your Google and YouTube data is never used to train generalized artificial intelligence (AI) or machine learning models without explicit consent.</li>
      </ul>

      <h2>4. Data Retention, Revocation & Deletion</h2>
      <p>
        We believe you should have complete control over your data:
      </p>
      <ul>
        <li><strong>Read-Only Access:</strong> Access to your third-party platforms is strictly read-only. We do not modify, publish, or delete your campaigns, videos, or channels.</li>
        <li><strong>Token Storage:</strong> OAuth authorization tokens are encrypted at rest using industry-standard AES-256 encryption and stored securely in Google Cloud.</li>
        <li><strong>Revoking Google Access:</strong> You may disconnect your Google or YouTube accounts at any time from within INHAUS BRAIN, or directly revoke access via the 
          <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer">Google Security Settings / Permissions page</a>.
        </li>
        <li><strong>Data Deletion Request:</strong> You can request permanent deletion of all your stored credentials and associated cached analytics by emailing <a href="mailto:privacy@inhauscorp.com">privacy@inhauscorp.com</a> or <a href="mailto:support@inhauscorp.com">support@inhauscorp.com</a>. Upon receipt, your data is wiped within 48 hours.</li>
      </ul>

      <h2>5. Third-Party Links & Disclosures</h2>
      <p>
        INHAUS BRAIN uses YouTube API Services. By using our YouTube integration, you are also bound by:
      </p>
      <ul>
        <li><a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener noreferrer">YouTube Terms of Service</a></li>
        <li><a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Privacy Policy</a></li>
      </ul>

      <h2>6. Contact Us</h2>
      <p>
        If you have any questions regarding this Privacy Policy or our security practices, please contact:
      </p>
      <p>
        <strong>Inhaus Corp / INHAUS BRAIN Compliance Team</strong><br>
        Email: <a href="mailto:privacy@inhauscorp.com">privacy@inhauscorp.com</a> | <a href="mailto:support@inhauscorp.com">support@inhauscorp.com</a><br>
        Website: <a href="https://brain.inhauscorp.com">https://brain.inhauscorp.com</a>
      </p>
    </div>
  </main>

  <footer>
    <p>&copy; 2026 INHAUS BRAIN by Inhaus Corp. All rights reserved.</p>
    <p>
      <a href="/">About</a> &bull;
      <a href="/privacy">Privacy Policy</a> &bull;
      <a href="/terms">Terms of Service</a> &bull;
      <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Google Privacy</a>
    </p>
  </footer>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/terms", response_class=HTMLResponse)
@router.get("/terms-of-service", response_class=HTMLResponse)
@router.get("/api/v1/terms", response_class=HTMLResponse)
async def terms_of_service():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Terms of Service - INHAUS BRAIN</title>
  <meta name="description" content="Terms of Service for INHAUS BRAIN and Inhaus Marketing API services.">
  <style>{COMMON_CSS}</style>
</head>
<body>
  <header>
    <div class="nav-container">
      <a href="/" class="brand-title">
        <span>⚡ INHAUS BRAIN</span>
        <span class="brand-badge">Platform</span>
      </a>
      <nav>
        <a href="/">About & Overview</a>
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms" class="active">Terms of Service</a>
      </nav>
    </div>
  </header>

  <main>
    <div class="doc-card">
      <h1>Terms of Service</h1>
      <div class="effective-date">Last Updated: September 10, 2026 | Effective Date: September 10, 2026</div>

      <p>
        Welcome to <strong>INHAUS BRAIN</strong>. These Terms of Service ("Terms") govern your access to and use
        of the INHAUS BRAIN website, dashboard, API endpoints, and related tools provided by Inhaus Corp ("Company", "we", "us").
      </p>

      <h2>1. Acceptance of Terms</h2>
      <p>
        By accessing or using INHAUS BRAIN, connecting OAuth accounts, or using our APIs, you agree to be bound by these Terms
        and our <a href="/privacy">Privacy Policy</a>. If you do not agree to these Terms, you may not use the Service.
      </p>

      <h2>2. Description of the Service</h2>
      <p>
        INHAUS BRAIN is an enterprise marketing intelligence platform that aggregates advertising and media performance data
        across Google Ads, YouTube, Meta (Facebook/Instagram), TikTok, and other platforms into real-time visual dashboards and structured analytical pipelines.
      </p>

      <h2>3. YouTube & Third-Party Platform Terms</h2>
      <div class="highlight-box">
        <h3>YouTube API Services Notice</h3>
        <p>
          INHAUS BRAIN uses the <strong>YouTube API Services</strong>. By connecting your YouTube account or viewing YouTube
          data on our platform, you explicitly agree to be bound by the 
          <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener noreferrer">YouTube Terms of Service</a>
          and acknowledge that Google processes your data under the 
          <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Privacy Policy</a>.
        </p>
      </div>

      <h2>4. User Responsibilities & Account Access</h2>
      <ul>
        <li>You must be authorized to connect ad accounts, YouTube channels, and analytics assets on behalf of your organization.</li>
        <li>You are responsible for maintaining the confidentiality of any access tokens, API keys, or login credentials issued to you.</li>
        <li>You agree not to reverse-engineer, exploit rate limits, or use the Service for any unlawful activities.</li>
      </ul>

      <h2>5. Data Rights & Limited Use</h2>
      <p>
        You retain all rights and ownership to the data fetched from your connected platforms. INHAUS BRAIN only accesses and processes
        this data to provide visualization, analytical reports, and campaign summaries as authorized by you.
      </p>
      <p>
        Our handling of Google and YouTube data strictly complies with the 
        <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">Google API Services User Data Policy</a>,
        specifically respecting Limited Use covenants.
      </p>

      <h2>6. Termination & Revocation</h2>
      <p>
        You may terminate your use of the Service at any time. You can revoke INHAUS BRAIN's access to your Google or YouTube account
        via the <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer">Google security settings page</a>.
        We reserve the right to suspend or terminate accounts that violate these Terms or abuse API limits.
      </p>

      <h2>7. Disclaimer of Warranties & Limitation of Liability</h2>
      <p>
        The Service is provided "as is" and "as available" without warranties of any kind, whether express or implied.
        In no event shall Inhaus Corp be liable for any indirect, incidental, special, consequential, or punitive damages
        arising from your use of the Service or reliance on third-party marketing platform metrics.
      </p>

      <h2>8. Changes to These Terms</h2>
      <p>
        We may update these Terms periodically. We will notify users of material changes by updating the "Last Updated" date above.
      </p>

      <h2>9. Contact Information</h2>
      <p>
        For inquiries concerning these Terms:
      </p>
      <p>
        <strong>Inhaus Corp</strong><br>
        Email: <a href="mailto:support@inhauscorp.com">support@inhauscorp.com</a><br>
        Website: <a href="https://brain.inhauscorp.com">https://brain.inhauscorp.com</a>
      </p>
    </div>
  </main>

  <footer>
    <p>&copy; 2026 INHAUS BRAIN by Inhaus Corp. All rights reserved.</p>
    <p>
      <a href="/">About</a> &bull;
      <a href="/privacy">Privacy Policy</a> &bull;
      <a href="/terms">Terms of Service</a> &bull;
      <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener">YouTube Terms</a>
    </p>
  </footer>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/", response_class=HTMLResponse)
@router.get("/about", response_class=HTMLResponse)
async def landing_page():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>INHAUS BRAIN - Marketing Intelligence & Unified Analytics Platform</title>
  <meta name="description" content="INHAUS BRAIN brings all your marketing, YouTube, Google Ads, Meta, and TikTok performance data into one high-performance dashboard.">
  <style>
    {COMMON_CSS}
    .hero {{
      text-align: center;
      padding: 3.5rem 1rem 2.5rem;
    }}
    .hero h1 {{
      font-size: 3rem;
      line-height: 1.15;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 1.25rem;
    }}
    .hero h1 span {{
      color: var(--primary);
    }}
    .hero-subtitle {{
      font-size: 1.2rem;
      color: var(--text-muted);
      max-width: 680px;
      margin: 0 auto 2rem;
      line-height: 1.6;
    }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.5rem;
      margin: 2.5rem 0;
    }}
    .feature-card {{
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.75rem;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .feature-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.06);
    }}
    .feature-icon {{
      font-size: 2rem;
      margin-bottom: 1rem;
    }}
    .feature-card h3 {{
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 0.5rem;
    }}
    .feature-card p {{
      font-size: 0.9rem;
      color: var(--text-muted);
      margin-bottom: 0;
    }}
    .compliance-banner {{
      background: #ffffff;
      border: 1px solid #c7d2fe;
      border-radius: 12px;
      padding: 2rem;
      margin: 2.5rem 0;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .compliance-banner h3 {{
      font-size: 1.2rem;
      color: var(--primary-dark);
    }}
    .compliance-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}
    .tag {{
      background: var(--primary-light);
      color: var(--primary-dark);
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      font-size: 0.825rem;
      font-weight: 600;
    }}
    .cta-btn {{
      display: inline-block;
      background: var(--primary);
      color: #ffffff;
      padding: 0.85rem 1.75rem;
      border-radius: 8px;
      font-weight: 600;
      text-decoration: none;
      transition: background 0.15s ease;
    }}
    .cta-btn:hover {{
      background: var(--primary-dark);
    }}
  </style>
</head>
<body>
  <header>
    <div class="nav-container">
      <a href="/" class="brand-title">
        <span>⚡ INHAUS BRAIN</span>
        <span class="brand-badge">Platform</span>
      </a>
      <nav>
        <a href="/" class="active">About & Overview</a>
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms">Terms of Service</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="brand-badge" style="display:inline-block; margin-bottom: 1rem;">Unified Marketing Intelligence</div>
      <h1>Welcome to <span>INHAUS BRAIN</span></h1>
      <p class="hero-subtitle">
        INHAUS BRAIN connects all your marketing platforms into a single intelligence command center.
        Consolidate metrics from Google Ads, YouTube, Meta, and TikTok into verifiable, auditable performance reports.
      </p>
      <div>
        <a href="/privacy" class="cta-btn">View Privacy Policy & Compliance</a>
      </div>
    </section>

    <div class="grid-3">
      <div class="feature-card">
        <div class="feature-icon">📊</div>
        <h3>Unified Analytics</h3>
        <p>Aggregate spend, reach, impressions, CTR, CPA, and ROAS across your paid media channels in a standardized data schema.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">▶️</div>
        <h3>YouTube & Video Insights</h3>
        <p>Read-only channel performance, watch-time attribution, and subscriber analytics via certified YouTube API integration.</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🔒</div>
        <h3>Enterprise Data Security</h3>
        <p>Encrypted credentials at rest, strictly read-only access, zero resale of customer data, and strict adherence to Google Limited Use.</p>
      </div>
    </div>

    <div class="compliance-banner">
      <h3>Verified Third-Party API Integrations & Trust Standards</h3>
      <p>
        INHAUS BRAIN operates with transparency. We access only the data you authorize and never modify your campaigns or channels.
      </p>
      <div class="compliance-badges">
        <span class="tag">Google Ads API Ready</span>
        <span class="tag">YouTube API Services Compliant</span>
        <span class="tag">Google API Services Limited Use Verified</span>
        <span class="tag">Meta Graph API</span>
        <span class="tag">TikTok Business API</span>
        <span class="tag">AES-256 Cloud Token Encryption</span>
      </div>
    </div>

    <div class="doc-card" style="text-align: center; padding: 2rem;">
      <h3 style="margin-bottom: 0.5rem;">Need Support or Have Questions?</h3>
      <p>Our team is available to assist you with onboarding, data exports, or data privacy requests.</p>
      <p><strong>Contact Support:</strong> <a href="mailto:support@inhauscorp.com">support@inhauscorp.com</a> &bull; <a href="mailto:privacy@inhauscorp.com">privacy@inhauscorp.com</a></p>
    </div>
  </main>

  <footer>
    <p>&copy; 2026 INHAUS BRAIN by Inhaus Corp. All rights reserved.</p>
    <p>
      <a href="/">About</a> &bull;
      <a href="/privacy">Privacy Policy</a> &bull;
      <a href="/terms">Terms of Service</a> &bull;
      <a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener">YouTube Terms</a> &bull;
      <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Google Privacy</a>
    </p>
  </footer>
</body>
</html>
"""
    return HTMLResponse(content=html)
