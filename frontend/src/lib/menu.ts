// Main navigation (mega menu). Edit labels and links here; the header renders this list.
// Style links point to collection pages; occasion links use the existing ?occasion= filter
// (supported values: Haldi, Wedding, Party, Festive).

export type MenuLink = {label: string; href: string};
export type MenuColumn = {title: string; links: MenuLink[]};
export type MenuItem = {label: string; href: string; columns: MenuColumn[]; feature?: {image: string; title: string; href: string}};

const occasions = ['Haldi', 'Wedding', 'Party', 'Festive'];
const occasionLinks = (base: string): MenuLink[] => occasions.map(o => ({label: o, href: `${base}?occasion=${o}`}));

export const salwarStyles: MenuLink[] = [
  {label: 'Anarkali Suits', href: '/collections/anarkali-suits'},
  {label: 'Kurta Sets', href: '/collections/kurta-sets'},
  {label: 'Palazzo Suits', href: '/collections/palazzo-suits'},
  {label: 'Sharara Suits', href: '/collections/sharara-suits'},
  {label: 'Patiala Suits', href: '/collections/patiala-suits'},
  {label: 'Jump Suits', href: '/collections/jump-suits'},
  {label: 'Kaftan', href: '/collections/kaftan'},
  {label: 'Indo Western', href: '/collections/indo-western'},
  {label: 'Co-ord Sets', href: '/collections/co-ord-sets'},
  {label: 'Crop Top Styles', href: '/collections/crop-top-styles'},
];

export const mainMenu: MenuItem[] = [
  {
    label: 'Wedding', href: '/collections/wedding',
    columns: [
      {title: 'Style', links: [
        {label: 'Wedding Lehengas', href: '/collections/lehengas?occasion=Wedding'},
        {label: 'Anarkali Suits', href: '/collections/anarkali-suits?occasion=Wedding'},
        {label: 'Sharara Suits', href: '/collections/sharara-suits?occasion=Wedding'},
        {label: 'Palazzo Suits', href: '/collections/palazzo-suits?occasion=Wedding'},
        {label: 'Gowns', href: '/collections/gown?occasion=Wedding'},
        {label: 'Indo Western', href: '/collections/indo-western?occasion=Wedding'},
      ]},
      {title: 'Occasion', links: occasionLinks('/collections/wedding')},
      {title: 'Collection', links: [
        {label: 'New Arrivals', href: '/collections/wedding?sort=newest'},
        {label: 'Bridal Edit', href: '/collections/bridal'},
        {label: 'Shop All Wedding', href: '/collections/wedding'},
      ]},
    ],
    feature: {image: '/images/gharara.webp', title: 'The Wedding Edit', href: '/collections/wedding'},
  },
  {
    label: 'Bridal', href: '/collections/bridal',
    columns: [
      {title: 'Style', links: [
        {label: 'Bridal Lehengas', href: '/collections/lehengas?occasion=Wedding'},
        {label: 'Bridal Gowns', href: '/collections/gown?occasion=Wedding'},
        {label: 'Bridal Sharara', href: '/collections/sharara-suits?occasion=Wedding'},
        {label: 'Bridal Anarkali', href: '/collections/anarkali-suits?occasion=Wedding'},
      ]},
      {title: 'Occasion', links: occasionLinks('/collections/bridal')},
      {title: 'Collection', links: [
        {label: 'New Arrivals', href: '/collections/bridal?sort=newest'},
        {label: 'Book a Bridal Fitting', href: '/appointment'},
        {label: 'Shop All Bridal', href: '/collections/bridal'},
      ]},
    ],
    feature: {image: '/images/maroon.webp', title: 'Bridal Couture', href: '/collections/bridal'},
  },
  {
    label: 'Gown', href: '/collections/gown',
    columns: [
      {title: 'Style', links: [
        {label: 'Anarkali Gowns', href: '/collections/gown?q=anarkali'},
        {label: 'Indo Western Gowns', href: '/collections/indo-western'},
        {label: 'Kaftan Gowns', href: '/collections/kaftan'},
      ]},
      {title: 'Occasion', links: occasionLinks('/collections/gown')},
      {title: 'Collection', links: [
        {label: 'New Arrivals', href: '/collections/gown?sort=newest'},
        {label: 'Shop All Gowns', href: '/collections/gown'},
      ]},
    ],
    feature: {image: '/images/navy.webp', title: 'Evening Gowns', href: '/collections/gown'},
  },
  {
    label: 'Salwar Kameez', href: '/collections/salwar-kameez',
    columns: [
      {title: 'Style', links: salwarStyles},
      {title: 'Occasion', links: occasionLinks('/collections/salwar-kameez')},
      {title: 'Collection', links: [
        {label: 'New Arrivals', href: '/collections/salwar-kameez?sort=newest'},
        {label: 'Price: Low to High', href: '/collections/salwar-kameez?sort=price-asc'},
        {label: 'Shop All Salwar Kameez', href: '/collections/salwar-kameez'},
      ]},
    ],
    feature: {image: '/images/green.webp', title: 'Salwar Kameez', href: '/collections/salwar-kameez'},
  },
  {
    label: 'Collections', href: '/products',
    columns: [
      {title: 'Style', links: salwarStyles},
      {title: 'Occasion', links: occasionLinks('/products')},
      {title: 'Collection', links: [
        {label: 'Wedding', href: '/collections/wedding'},
        {label: 'Bridal', href: '/collections/bridal'},
        {label: 'Gown', href: '/collections/gown'},
        {label: 'Salwar Kameez', href: '/collections/salwar-kameez'},
        {label: 'Lehengas', href: '/collections/lehengas'},
        {label: 'New Arrivals', href: '/products?sort=newest'},
        {label: 'View All', href: '/products'},
      ]},
    ],
    feature: {image: '/images/collection.webp', title: 'All Collections', href: '/products'},
  },
];
