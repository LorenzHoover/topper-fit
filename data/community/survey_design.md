# FitMyTopper Community Survey — Design Doc

**Google Form title:** "Real-World Truck Topper Fits — Share Your Story"
**Google Form description (shown at top):**
> I'm building a free fitment lookup tool for truck toppers. Manufacturer spec sheets only
> cover OEM fits — but plenty of truck owners have made a "wrong" topper work.
> That knowledge exists only in forum posts and people's heads. Help me change that.
> This will take under 3 minutes. Your story will be credited on the site.

---

## Section 1 — Your Truck

**Q1: What year is your truck?**
Type: Short answer (number)

**Q2: What's your truck's make?**
Type: Dropdown
Options: Chevrolet, Dodge, Ford, GMC, Honda, Isuzu, Jeep, Nissan, Ram, Toyota, Other

**Q3: What's your truck's model?**
Type: Short answer
Helper text: e.g. F-150, Silverado 1500, Tacoma, Tundra, Ranger, Canyon, Ram 1500

**Q4: What's your cab style?**
Type: Multiple choice
Options:
- Regular Cab (2-door, short cab)
- Extended Cab / Access Cab (2-door, longer cab — rear jump seats or small doors)
- Double Cab / Quad Cab (4-door, shorter rear doors)
- Crew Cab / SuperCrew / CrewMax (4-door, full-size rear doors)
- Not sure

**Q5: What's your bed length?**
Type: Multiple choice
Options:
- Short bed (~5–5.5 ft)
- Standard / mid bed (~6–6.5 ft)
- Long bed (~8 ft)
- Not sure

**Q5b: If you've measured your bed floor (front wall to tailgate), what's the length in inches?**
Type: Short answer (optional)
Helper text: This helps us match your truck exactly. Measure inside the bed, not outside.

---

## Section 2 — Your Topper

**Q6: What brand is your topper?**
Type: Short answer
Helper text: e.g. LEER, Ranch, ARE, ATC, SnugPro, Century, Jason, unknown

**Q7: What model or series is your topper?**
Type: Short answer (optional)
Helper text: e.g. "100XL", "Rebel", "Express", "DCU" — check inside the topper or the original listing

**Q8: What truck was this topper ORIGINALLY made for?**
Type: Short answer
Helper text: What does the label say, or what truck was it listed for when you bought it?
e.g. "2014-2018 Toyota Tacoma Double Cab Short Bed" or "F-150 2015-2020 SuperCrew"

**Q9: How did you end up with a non-OEM fit?**
Type: Checkboxes (select all that apply)
Options:
- Different year range of the same truck (e.g. previous gen Tacoma on current gen)
- Different cab style on the same truck (e.g. regular cab shell on a crew cab)
- Different make or model entirely (e.g. F-150 shell on a Tundra, Tacoma shell on a Ranger)
- Bought it used and it came with the wrong fit
- Intentional — found a deal and made it work
- Other (explain below)

---

## Section 3 — How It Fits

**Q10: How would you rate the overall fit?**
Type: Multiple choice
Options:
- ✅ Perfect seal — looks like it belongs, no gaps, no overhang
- 🟡 Good enough — minor gaps I sealed with weatherstrip, barely noticeable
- 🟠 Noticeable issues — gaps or overhang visible, took some work
- 🔴 Rough fit — significant modification required, but it works
- ❌ Didn't work — I gave up or reversed the install

**Q11: Where does the topper NOT align well?**
Type: Checkboxes (select all that apply)
Options:
- Front (cab end) — overhang or gap
- Rear (tailgate end) — overhang or gap
- Driver side
- Passenger side
- Corner gaps (front or rear corners)
- Vertical height — sits too high or too low compared to cab roofline
- Fits great, no alignment issues

**Q12: Approximately how much does it overhang or fall short? (if applicable)**
Type: Short answer (optional)
Helper text: e.g. "about 1 inch forward at the front" or "1/2 inch gap on the driver side"

---

## Section 4 — The Goldmine: What Did You Do?

**Q13: What modifications did you make to the TOPPER to make it work?**
Type: Paragraph (long text)
Helper text: e.g. added foam weatherstripping along the rail, trimmed the rear seal,
relocated mounting clamps, cut/trimmed the front flange, added spacers

**Q14: What modifications did you make to the TRUCK to make it work?**
Type: Paragraph (long text)
Helper text: e.g. drilled new clamp holes, added rail extensions, modified weatherstrip channel,
nothing at all

**Q15: What clamps or hardware did you use?**
Type: Short answer (optional)
Helper text: OEM clamps, aftermarket (brand?), ratchet straps, self-tapping screws, etc.

**Q16: Any tips you'd give someone trying this same combo?**
Type: Paragraph (long text, optional)
Helper text: This is gold. Anything you wish you'd known before you started.

**Q17: Would you do this again / recommend it to others?**
Type: Multiple choice
Options:
- Yes — works great, would do it again
- Yes with caveats — works but more effort than expected
- Probably not — more trouble than it's worth
- No — regret it

---

## Section 5 — Photos & Credit

**Q18: Upload a photo (optional but incredibly helpful)**
Type: File upload
Helper text: A photo of the topper on your truck, especially showing any gaps, overhang,
or your modification. Worth more than a thousand words.

**Q19: What's your Reddit username, forum handle, or name? (optional)**
Type: Short answer
Helper text: We'll credit you on the site. Leave blank to stay anonymous.

**Q20: Anything else we should know?**
Type: Paragraph (optional)

---

## Confidence Score Mapping (internal — not shown in form)

| Q10 Answer | fit_type candidates | confidence |
|---|---|---|
| Perfect seal | cross_generation / cross_make / cross_cab | 85 |
| Good enough | cross_generation / cross_make / cross_cab | 70 |
| Noticeable issues | with_modification | 60 |
| Rough fit | with_modification | 50 |
| Didn't work | incompatible | 0 |

Cross-type is determined by Q8 vs Q2/Q3:
- Same make/model, different year → cross_generation
- Same make/model/year, different cab → cross_cab
- Different make or model → cross_make

---

**Google Form link to share:** [paste after creating]
**Google Sheet export URL:** [paste after linking responses]
