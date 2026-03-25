import React from 'react'
import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav__brand">O2C Intelligence</div>
        <Link to="/workspace" className="landing-nav__cta">
          Open Workspace
        </Link>
      </nav>

      {/* Hero */}
      <section className="hero">
        {/* Floating dots background */}
        <div className="hero__bg-dots">
          <div className="hero__bg-dot" />
          <div className="hero__bg-dot" />
          <div className="hero__bg-dot" />
          <div className="hero__bg-dot" />
          <div className="hero__bg-dot" />
          <div className="hero__bg-dot" />
        </div>

        <div className="hero__content">
          <div className="hero__eyebrow">Order-to-Cash Intelligence</div>
          <h1 className="hero__title">See how your business flows.</h1>
          <p className="hero__subtitle">
            Query your order-to-cash system. Trace every document.
            Get exact, data-backed answers in seconds.
          </p>
          <Link to="/workspace" className="hero__cta">
            Open Workspace
            <span className="hero__cta-arrow">→</span>
          </Link>
          <div className="hero__shortcut">
            Press <kbd>/</kbd> in workspace to start querying
          </div>

          {/* W3-1: Sample query chips — show users exactly what they can ask */}
          <div className="hero__samples">
            <span className="hero__samples-label">Try asking:</span>
            <div className="hero__sample-chips">
              {[
                'Trace the full lifecycle of Sales Order 5001',
                'Which deliveries were never billed?',
                'Top 5 customers by net amount',
              ].map(q => (
                <Link key={q} to={`/workspace?q=${encodeURIComponent(q)}`} className="hero__sample-chip">
                  {q}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <div className="features__content">
          <div className="features__label">Capabilities</div>
          <h2 className="features__heading">
            Built for precision, not guesswork.
          </h2>
          <div className="features__grid">
            <div className="feature">
              <div className="feature__icon">⬡</div>
              <div className="feature__title">Trace flows</div>
              <div className="feature__desc">
                Follow any document from sales order through delivery,
                billing, journal entry, to payment. See the full path.
              </div>
            </div>
            <div className="feature">
              <div className="feature__icon">◇</div>
              <div className="feature__title">Detect gaps</div>
              <div className="feature__desc">
                Find orders delivered but not billed, invoices without
                payments, and broken flows automatically.
              </div>
            </div>
            <div className="feature">
              <div className="feature__icon">▹</div>
              <div className="feature__title">Answer instantly</div>
              <div className="feature__desc">
                Ask questions in plain language. Get structured,
                data-grounded answers with full traceability.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="trust">
        <div className="trust__content">
          <h2 className="trust__heading">Built to be trusted.</h2>
          <p className="trust__subtitle">
            Every answer is grounded in your data.
            No hallucinations. No guesswork.
          </p>
          <div className="trust__items">
            <div className="trust__item">
              <div className="trust__item-value">100%</div>
              <div className="trust__item-label">Deterministic</div>
            </div>
            <div className="trust__item">
              <div className="trust__item-value">0</div>
              <div className="trust__item-label">Hallucinations</div>
            </div>
            <div className="trust__item">
              <div className="trust__item-value">&lt;1s</div>
              <div className="trust__item-label">Response time</div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div>O2C Graph Intelligence</div>
        <div className="footer__links">
          <a
            href="https://github.com/Scarage1/Destiny1"
            className="footer__link"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <Link to="/workspace" className="footer__link">
            Workspace
          </Link>
        </div>
      </footer>
    </div>
  )
}
