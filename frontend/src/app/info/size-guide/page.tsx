import {get} from '@/lib/server';
import {HomeSizeGuide, type SizeGuideData} from '@/components/home-extras';

export const metadata = {title: 'Size Guide', description: 'Aiman Royale size chart in inches and centimetres, with how-to-measure steps.', alternates: {canonical: '/info/size-guide'}};

// Size chart and measuring steps come from admin → Size chart rows / How-to-measure steps.
export default async function SizeGuidePage() {
  const guide = await get<SizeGuideData>('size-guide/').catch(() => null);
  return <div className="info-page">
    <div className="info-head"><p className="eyebrow">Find your perfect fit</p><h1>Size Guide</h1><p>Compare your measurements with our chart in inches or centimetres. Need something made to measure? Choose <strong>Custom Measurements</strong> on any style.</p></div>
    {guide ? <HomeSizeGuide title="Size chart" guide={guide}/> : <p className="info-head">The size chart is being updated. Please contact us for help with sizing.</p>}
  </div>;
}
