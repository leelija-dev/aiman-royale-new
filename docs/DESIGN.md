# Design implementation map

The visual direction follows the supplied ivory, champagne and burgundy concepts, with italic Aiman Royale wordmark, editorial serif headings, generous spacing, portrait product cards and understated borders.

| Supplied reference | Implemented route / section |
| --- | --- |
| 1000066857.png | Homepage hero, collections, favourites, celebration edit, fitting CTA, newsletter and footer |
| 1000066858.png | `/products`: editorial banner, catalogue filtering/sort and product grid |
| 1000066860.png | `/collections/[slug]`: collection banner and collection-specific Haldi/Wedding/Party/Festive filters |
| 1000066861.png | `/login`: editorial photograph and sign-in panel |
| 1000066862.png / 1000066867.png | `/products/[slug]`: product gallery, options, custom measurements, purchase buttons and details |
| 1000066863.png | `/cart`: items, quantity adjustment and order summary |
| 1000066864.png | `/register`: email form and configurable WhatsApp OTP stages |
| 1000066865.png | `/checkout`: delivery details, payment choice and summary |
| 1000066866.png | `/appointment`: hero, session choice, real available date/time selection, contact form and guidance |

The implementation uses live form controls and database availability in place of decorative mockup controls. Appointment scheduling uses an accessible available-date select and real time buttons rather than a static calendar. Payment details are collected by the payment provider's secure checkout. No decorative reviews or invented customer ratings are included.

Original product photographs from Aiman Royale are saved as high-quality resized WebP seed assets. Editorial crops from the reference PNGs are lower-resolution source material; replace them with your original high-resolution photography in a final production asset pass. Resizing cannot recover detail absent from a screenshot.

Desktop/mobile CSS is implemented at 1200, 900 and 700 pixels. Browser visual verification was unavailable in this environment; exact pixel matching and layout overflow checks remain staging review tasks. The source is editable and is not a screenshot flattened into a web page.
