# To Do List

## Common prompt hats

Please provide with the final complete code for _ with your suggested changes

## Must

Make it faster: Why is taking so long to extract the images if we do not want to actually extract any images only get the urls of them, I feel like that should be way faster, oh we should also try to scroll down on every look to ensure every image is there, and well loaded before seeking for the urls

Recommendations to improve the structure of this project?, Are there files that are not used in this project?

It should go to gmail to pick the code: ADD IF LINK HAS EXPIRED IT GOES TO GMAIL TO GET A NEW LINK

I feel as if there is something off in the logs check them out

Hacer un visualizador for the redis db

Run with 8 workers in the ai machine

## Should

Run to find discrepancies in the redis db images emptys, looks emptys, designers emptys, seasons emptys etc.
Vectorize every image features
Make a visualizer of each outfit with its closest neighbors using RESNET
Make a searcher using CLIP

## Could

...

## Wont

...

## Done

1. Fix: WARNING - Error processing season group: Message: no such element: Unable to locate element: {"method":"css selector","selector":".NavigationHeadingWrapper-befTuI"}
2. Fix: - WARNING - Failed to extract image data: Message: no such element: Unable to locate element: {"method":"tag name","selector":"img"}
  (Session info: chrome=131.0.6778.265); For documentation on this error, please visit: <https://www.selenium.dev/documentation/webdriver/troubleshooting/errors#no-such-element-exceptio>
  
Arreglar el checkpoint de redis

Modularize (no files of more than 300 lines)

Modularizar

It is still going to <https://www.vogue.com/article/> which is undesired articles should not be webscraped, example: 2025-02-24 18:40:58,318 - INFO - Starting session for designer: The Winter Escape Wardrobe: 5 Resort Trends to Shop Now

when it goes to a season it should take the designers from:

<a role="link" class="NavigationInternalLink-cWEaeo kHWqlu grouped-navigation__link link--secondary navigation__link" href="/fashion-shows/fall-2024-ready-to-wear/talia-byre" data-testid="navigation__internal-link">Talia Byre</a>

Because where it is currently taking the designers from it has show more button that we are not taking into account

Run on raspberry pi

Handle Collections that do not have a View Slideshow button and just looks like that

The

    "overall_progress": {
      "total_seasons": 0,
      "completed_seasons": 0,
      "total_designers": 0,
      "completed_designers": 0,
      "total_looks": 0,
      "extracted_looks": 0
    }

Is not being updated in real time, we should also add to that object like an elapsed time and estimated time

The
          "total_looks": 0,
          "extracted_looks": 0,
is not being updated real time

Not any one timing field is being added to the json
