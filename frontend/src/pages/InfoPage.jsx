import { useParams } from 'react-router-dom';

const PAGES = {
  about: {
    title: 'About Us',
    body: 'ORELLE is a modern fashion label built for everyday movement — clean silhouettes, honest fabrics, and pieces designed to outlast a season. We design for Men, Women, and Juniors from our studio, with a small footprint and a focus on fit.',
  },
  contact: {
    title: 'Contact Us',
    body: 'Reach our customer care team at support@orelle.pk or call 0800-ORELLE, Monday to Saturday, 10am–7pm. We usually respond within one business day.',
  },
  faq: {
    title: 'FAQ',
    body: 'Do I need an account to order? No — checkout as a guest and track your order using your order number and email. What payment methods do you accept? Cash on Delivery, Bank Transfer, and Card. How long does delivery take? 5–7 working days standard, 2–4 working days express.',
  },
  shipping: {
    title: 'Shipping Policy',
    body: 'Standard delivery takes 5–7 working days across Pakistan. Express delivery (2–4 working days) is available at checkout. Orders above PKR 5,000 ship free.',
  },
  returns: {
    title: 'Returns Policy',
    body: 'Items can be returned within 14 days of delivery if unworn, unwashed, and with original tags attached. Start a return from My Account > Orders, selecting the item and a reason. Refunds are processed within 5–7 working days of approval.',
  },
  exchanges: {
    title: 'Exchange Policy',
    body: 'Need a different size or color? Request an exchange from My Account > Orders within 14 days of delivery. Exchanges are subject to stock availability.',
  },
  'size-guide': {
    title: 'Size Guide',
    body: 'Refer to the Size Guide on each product page for garment-specific measurements. As a general rule: S fits 36" chest, M fits 38", L fits 40", XL fits 42".',
  },
  privacy: {
    title: 'Privacy Policy',
    body: 'We collect only the information needed to process your orders and improve your shopping experience. We never sell your data to third parties. For questions, contact privacy@orelle.pk.',
  },
};

export default function InfoPage() {
  const { page } = useParams();
  const content = PAGES[page] || { title: 'Not Found', body: 'This page does not exist.' };

  return (
    <div className="max-w-2xl mx-auto px-4 py-20">
      <h1 className="font-display text-3xl uppercase mb-6">{content.title}</h1>
      <p className="text-ink-soft leading-relaxed">{content.body}</p>
    </div>
  );
}
