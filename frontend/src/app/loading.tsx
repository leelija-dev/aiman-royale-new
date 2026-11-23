// Shown while a page streams in. It fills the screen so the footer never flashes near the top and then
// jumps down when the page arrives (that jump was the big Cumulative Layout Shift in PageSpeed).
export default function Loading(){return <section className="section empty route-loading" aria-busy="true"><p className="eyebrow">AIMAN ROYALE</p><h2>A beautiful moment is on its way…</h2></section>}
