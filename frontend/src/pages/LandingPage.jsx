import React from "react";
import Button from "../components/ui/Button";

const features = [
  {
    title: "RTL Perfection",
    description: "Preserves right-to-left direction in DOCX with high accuracy.",
  },
  {
    title: "Smart Layout",
    description: "Uses advanced layout models to structure output properly.",
  },
  {
    title: "Freemium Tiers",
    description: "Free up to 50 pages/month, with premium plans for professionals.",
  },
];

function LandingPage({ openLogin, openRegister }) {
  return (
    <div className="min-h-screen bg-background text-content dark:bg-background-dark dark:text-content-light font-sans">
      {/* Hero */}
      <section className="text-center py-20 px-4">
        <h1 className="text-4xl sm:text-5xl font-extrabold mb-4 text-secondary">
          Convert Arabic PDFs to DOCX with Precision
        </h1>
        <p className="max-w-2xl mx-auto text-lg text-content-muted mb-8">
          TextAra makes it easy to preserve layout, directionality, and structure when converting Arabic documents.
        </p>
        <div className="flex justify-center gap-4">
          <Button onClick={openRegister} variant="primary" className="text-lg px-6 py-3">
            Get Started
          </Button>
          <Button onClick={openLogin} variant="secondary" className="text-lg px-6 py-3">
            Log In
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="bg-background-subtle dark:bg-primary-light py-16">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-6 text-content">Why Choose TextAra?</h2>
          <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-3">
            {features.map(({ title, description }) => (
              <div
                key={title}
                className="p-6 bg-primary-light shadow rounded border border-primary-dark dark:border-content-muted"
              >
                <h3 className="text-xl font-semibold text-secondary mb-2">{title}</h3>
                <p className="text-content-muted">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-primary-dark text-content-light text-center px-4">
        <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
        <p className="text-lg mb-6">Create an account and convert your first Arabic PDF in seconds.</p>
        <Button onClick={openRegister} variant="primary" className="px-6 py-3 text-lg">
          Sign Up Now
        </Button>
      </section>
    </div>
  );
}

export default LandingPage;
