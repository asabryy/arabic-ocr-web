import React from "react";
import { Link } from "react-router-dom";
import Button from "../components/ui/Button"; // <-- make sure this is imported

function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-gray-900 font-sans">
      <section className="text-center py-20 px-4">
        <h1 className="text-4xl sm:text-5xl font-extrabold mb-4 text-brand">
          Convert Arabic PDFs to DOCX with Precision
        </h1>
        <p className="max-w-2xl mx-auto text-lg text-gray-600 mb-8">
          TextAra makes it easy to preserve layout, directionality, and structure when converting Arabic documents.
          Get started today for free or upgrade for more power.
        </p>
        <div className="flex justify-center gap-4">
          <Link to="/register">
            <Button className="text-lg px-6 py-3" variant="primary">
              Get Started
            </Button>
          </Link>
          <Link to="/login">
            <Button className="text-lg px-6 py-3" variant="secondary">
              Log In
            </Button>
          </Link>
        </div>
      </section>

      <section className="bg-white py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-6 text-gray-800">Why Choose TextAra?</h2>
          <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-3">
            <div className="p-6 rounded-2xl shadow-md bg-background">
              <h3 className="text-xl font-semibold text-brand mb-2">RTL Perfection</h3>
              <p className="text-gray-600">Preserves right-to-left direction in DOCX with high accuracy.</p>
            </div>
            <div className="p-6 rounded-2xl shadow-md bg-background">
              <h3 className="text-xl font-semibold text-brand mb-2">Smart Layout</h3>
              <p className="text-gray-600">Uses advanced layout models to structure output properly.</p>
            </div>
            <div className="p-6 rounded-2xl shadow-md bg-background">
              <h3 className="text-xl font-semibold text-brand mb-2">Freemium Tiers</h3>
              <p className="text-gray-600">Free up to 50 pages/month, with premium plans for professionals.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-brand text-white text-center px-4">
        <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
        <p className="text-lg mb-6">
          Create an account and convert your first Arabic PDF in seconds.
        </p>
        <Link to="/register">
          <Button className="bg-white text-brand font-bold hover:bg-background transition">
            Sign Up Now
          </Button>
        </Link>
      </section>
    </div>
  );
}

export default LandingPage;