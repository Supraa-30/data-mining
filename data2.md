SetuBid aggregates public procurement notices scraped from 260governmnet portals. A single tender is routinely published on several portals , then re-published after a corrigendum, then re-published again by a nodal agency that reformats it. Each copy carries a different reference number, a different date and slight different wording. There is no shared identifier anywhere. Bidder pay for SetuBid because it promise: "One opportunity,one card."Today the product shows a bidder the same road-widening contract nine times and the biddert pays a subscripation to see it in ninetimes.Meanwhile the operations team has been trying to fix this with a nightly job that comparess every notice against every other notice. Last month that job ran for 31 hours and was killes. The copus grows by roughly 4000 notices a week and the board  has asked for the deduplication to finish inside a 20 minute nightly window on one machine forever. The Head of Product adds 2 constraints thats she refuses to negotiate.

"First- if we merge 2 tenders that were actually different, a bidder misses a deadline and sues us. If we fail to merge two tenders that were the same, a bidder sees a duplicate card and grumbles. Those 2 mistakes are not the same size,and I want to see that asymmetry in your setting as a number , not as an adjective.

Second- The card ID that bidder bookmarks today must still point at the same opportunity next month, even though we will have re run the whole pipeline thirty times by then and the cluster will have absorbed new copies.If bookmarks break, we lose the account "


this is the structure of the data:

├── data_2/
│   ├── labelled_pairs.csv
│   ├── portal_profiles.md
│   ├── _truth/
│   │   └── ...
│   ├── notices/
│   │   └── ...
│   └── ...


Section A: FROM AN INTERACTABLE COMPARISON TO A TRACTABLE ONE 

1.DEFINE WHAT "SIMILAR" MEANS HERE, MECHANICALLY: before anaything can be comopared cheaply it must be comparable at all. commit to a way of turning a notice into something over which a similarity score between 2 notices is well defined and state the score. ur choice involves at least one decision abt how finely the text is decomposed and at least 1 decisionabt which parts of the text are signal and which are noise, the corpus contains monetary amts dates reference numbers and portal boilerplates and it is for u to say what beconmes of them. defend both decisions with evidence from this corpus rather than from a reference: take a pair labelled same n a pair labbelloed different show how the score separates them under 2 counyting choices and say which u adopted n what the adoption cost

2.TRADE EXACTNESS FOR SPACE, DELIBARATELY: retaining the exact representation for the whole corpus is not affordable so u will hold a reduced form of each notice n accept that the similarity u compute from it is an estimate. fix the size of that reduced form beforeu implement it by stating the estimation accuracy the application needs and arguing from that requirement to a size. then close the loop measure the realised error against labelled_pairs.csv and report whether the estimator behaved as ur argument predicted including where it did not. a size adopted because it is a rounf number, or because a tutorial used it, earns nothing here even if the system works.

3.MAKE RETRIVAL SUBLINEAR AND PRICE THE RISK: the nightly budget rules out scoring each notice against the corpus os u need a way ro retrive for any notice, a short candidate list that is very likey to already contqain its trueduplicates. build one, whatever u build will expose a tunable tension between how reliably a genuinely similar pair is retrived and how much work the candidate lists create; ur task is to make that tension explicit rather than incidental. charaterise as a function of true similarity the probability that a pair survives to the candidate stage; plot it; and mark on the plot the operating point u chose. then justify that point in the head of product's terms, her two failure modes have different costs abd ur answer shld show where that ratio entered ur settings.

SECTION B: MAKING IT A DATABASE PROBLEM, NOT A SCRIPT

4.GIVE THE RETRIEVAL STRUCTURE A HOME AND AN ACCESS PATH:Give the retrival structure a home and an access path. Whatever your schema in (c) consult at lookup time must live as relational data that survives a process restart and can be queried by the application -- not in a Python object that dies with the job. design that schema. Then make a considered choce of acess method for lookup, and justify it by reference to how the candidate methods physically locate rows, nameing at least one alternative you rejected and why it loses here. Support the arguments with measurements rather than asserions: the planners chosen path, the rows actually examined, and wall-clock time, with the rejected alternative forced for comparison.

5.FIND THE PLACE WHERE THE DESIGN BETRAYS YOU:Find the place where the design betrays you. Run your retrival over the full corpus and look at how the works is ditributed across notices rather than at its total. IT will be badly uneven, and a small part of the corpus will be responsible for a disproportionate share of the nightly cost. Locate that part empirically;portal_profiles.md will help you interpret what you find. Then do three things:explain in mechanical term why this property of the data interacts your design to produce the distribution you observe; quantify what it costs you against the 20-minutes budget; and migrate it. Report the disrtibution and the runtime before and after, and state plainly what the mitigation cost you in retrival quality, measured on the lebelled pairs. A mitigation whose proce is not measured is not accepted.
