Based on conversation with my dad on Oct 25 2017.  He showed me video on how woodblock prints are made, in particular [this one](https://cdn.shopify.com/s/files/1/0608/2925/products/RickshawCart1_1_1024x1024.jpg) he got me.  So I was thinking about various mechanisms for translating rotational energy into a stamp-and-reload-with-ink motion.  I think making a machine that can do this as multiple distinct movements would be super cool and fun to watch, but I think with 3d printing there might be a much simpler mechanism that could work.   


Key feature: instead of molds of the image on a flat 2d plane, make molds which create a silicone cylinder with the image wrapped around it. As paper rolls along each of multiple cylinders, each transfers one color to create the final image.

Design:
- There are a number of colorStampUnits, one for each color.  Ideally should have a built-in common connector (like a jigsaw puzzle piece edge/dovetail joint) so they can easily and sturdily be connected in series.
- On either end of the colorStampUnits, there is paper-roll-feeding unit at the beginning, and a paper cutting unit at the end.  Somewhere in the assembly is a hand crank or other 'drive' mechanism.
- All units are driven with a common chain or belt, so the internal mechanisms of each all rotate at the same rate. Could do with a series of gears for cooler aesthetic (but probably a bit less accurate because of tolerances between where gear teeth meet).
- A colorStampUnit consists of: {
  - a tray of ink
  - a foam roller, which rolls through the surface of the ink tray and transfers the ink to the patterned silicone roller.
  - Silicone patterned roller 'cast' from a 3d printed negative.  Like a woodblock print, only the sections of the cylinder at full thickness touch the paper.  Negative voids prevent ink transfer in the selected areas.  Because it's silicone (flexible), you might be able to do something tricky where you print it out in 2d and wrap/clamp it around a cylinder. May also be some new flexible print materials that would be suitable stamp material.  These should be easily swappable so colorStampUnit can be reconfigured to print different images.
  - maybe a squeegee to keep amount of ink on roller moderate and consistent
  - a mechanism which guides the paper along the surface of the roller. perhaps an additional opposite roller applying pressure to the back of the print area. maybe a plate behind the paper where the roller is pressing, maybe a conveyor belt over a plate?
  - gear teeth on the ends of the foam and silicone rollers could keep them rotationally locked and moving at a constant speed, and allow them to be driven by the main drive chain.
}
- end unit: paper cutting unit can just be a guillotine on a crank, with safety guards to keep fingers out. 
- start unit: paper roll dispenser unit just needs a gear on the side of the roll
- for initial/smaller batches, may be able to load foam rollers with ink by hand.


Challenges:
- keeping all units rotationally locked.  tolerances too high will create 'blurry' images
- moderating amount of ink.  this is probably a solved problem, but i imagine keeping a constant amount of ink on a roller is not necessarily easy.
- keeping the paper taut but not so much that it rips.  May want some rollers to pull slightly more than they should to apply consistent forward pressure along the length of the paper.  perhaps some small rollers in the end unit that would only touch the edges of the paper outside of the print area?  Keeping taut width-wise also a concern
- guillotine cutting constantly moving paper is tricky.  may want main drive to be driven by gear with some teeth missing so paper stops during part of the cycle (and is then cut).  Can you make a diagonal cut on a constantly moving piece of paper to get a square end?
- I think the smaller you can make this device, the cooler it'd be.  
- having ink tray/roller above print medium seems dangerous.  wonder if paper could be above the silicone rollers above the foam above the ink tray, so ink would fall back down into the tray.
- would be nice to be able to clean the color out of a unit, probably a challenge to make cleaning this easy.
- would be cool to make this work for sheets of paper instead of rolls, probably means adding lots of guide rollers
