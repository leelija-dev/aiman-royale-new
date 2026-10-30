'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <section className="section empty"><p className="eyebrow">AIMAN ROYALE</p><h1>A little pause.</h1><p>We couldn’t load this page. Please try again shortly.</p><button className="button" onClick={reset}>Try Again</button></section>}
