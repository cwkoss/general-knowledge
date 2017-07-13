# software
- better software for this
  - the general idea of how i want to use this github page is: mind dump as many thoughts as I can into it, generally sorted by category.  If it's short or incomplete, just leave it in the category page.  Once the idea is big enough put it into it's own page, but link to it with a shorter blurb from the category.  I'll occasionally read over the pages, and either add new stuff or revise and add to old stuff: generally, the interesting ideas will grow in total content: i'll write more questions, musings, specifications, opportunities for different things. 
  - a better system could:
    - put all of the content in a big nested tree - basically a big ass bulleted list that defaults to having sections collapsed.  
      - you start from the table of contents and click on a category to see the stuff inside it.  I think there should maybe be two kinds of expand: subtopics (show child nodes) and more info (show more local node info, ideally prose which contains those subtopics linked and source of previous list). Nodes should be able to link to any other nodes, so much like browsing wikipedia, where you might start reading about blue whales and then open a new tab on buoyancy > gravity > orbits,  your state contains the 'stack' of your train of thought, allowing you to re-collapse buoyancy and get back to learning about blue whales.  Multiple parent links allow the same node to be contained by multiple categories/parent nodes. 
      - typeahead for other nodes.  editor could open a typeahead on the '[' character, and then you could type or select a suggested other node based on what you've typed so far.  wrap a potential node name in '[' ']' to indicate you intend to add a node there later.
      - nodes should have: a title, short prose, long prose. prose contains links. maybe even go crazy and add in a medium.
      - in displaying the nodes, would be cool to have visual indicators of what nodes you've used the most, or maybe even change the defaults for what starts expanded. 
      - store 'infinite stack' so you can see what you've previously expanded and go back to it through the same path
      - each author should have their own table of contents, but cross linking and forking nodes is interesting
- plant planner app
  - helps you plan what plants youre going to grow when where and how
  - input your growing locations (size, sunlight, soil type, etc), desired plants, and location
  - it uses almanacs and shit to figure out which plants should be planted where, and when you should perform different steps.
  - notifications for when to plant, maintain, and harvest
- opsgenie for farming
  - make tasks for a farm that happen on a schedule, ex. water the plant once every 3 days. 
  - someone owns this task, it will remind them to do it before, and ask them to confirm after.
  - if a task isn't confirmed in time, a fallback person is notified that they need to pick up the original owners task
  - tasks have props: name, interval, remind_time, completion_time, Person owner, Person completer

  
