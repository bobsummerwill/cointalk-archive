<html><body>/**
 * author Christopher Blum
 *    - based on the idea of Remy Sharp, http://remysharp.com/2009/01/26/element-in-view-event-plugin/
 *    - forked from http://github.com/zuk/jquery.inview/
 */
(function ($) {
  var inviewObjects = {}, viewportSize, viewportOffset,
      d = document, w = window, documentElement = d.documentElement, expando = $.expando;

  $.event.special.inview = {
    add: function(data) {
      inviewObjects[data.guid + "-" + this[expando]] = { data: data, $element: $(this) };
    },

    remove: function(data) {
      try { delete inviewObjects[data.guid + "-" + this[expando]]; } catch(e) {}
    }
  };

  function getViewportSize() {
    var mode, domObject, size = { height: w.innerHeight, width: w.innerWidth };

    // if this is correct then return it. iPad has compat Mode, so will
    // go into check clientHeight/clientWidth (which has the wrong value).
    if (!size.height) {
      mode = d.compatMode;
      if (mode || !$.support.boxModel) { // IE, Gecko
        domObject = mode === 'CSS1Compat' ?
          documentElement : // Standards
          d.body; // Quirks
        size = {
          height: domObject.clientHeight,
          width:  domObject.clientWidth
        };
      }
    }

    return size;
  }

  function getViewportOffset() {
    return {
      top:  w.pageYOffset || documentElement.scrollTop   || d.body.scrollTop,
      left: w.pageXOffset || documentElement.scrollLeft  || d.body.scrollLeft
    };
  }

  function checkInView() {
    var $elements = $(), elementsLength, i = 0;

    $.each(inviewObjects, function(i, inviewObject) {
      var selector  = inviewObject.data.selector,
          $element  = inviewObject.$element;
      $elements = $elements.add(selector ? $element.find(selector) : $element);
    });

    elementsLength = $elements.length;
    if (elementsLength) {
      viewportSize   = viewportSize   || getViewportSize();
      viewportOffset = viewportOffset || getViewportOffset();

      for (; i<elementslength; !viewportsize)="" $element="$(element)," $element.height(),="" $element.width()="" $elements[i]))="" 'display:none'="" 'none')="" 'visibility:hidden'="" (!$.contains(documentelement,="" (!viewportoffset="" (element.offsetwidth="" 5.="" ::="" above="" and="" are="" ask="" because="" by="" case="" closer="" container="" continue;="" correct="" count="" dom="" don't="" element="$elements[i]," elementoffset="{}," elementoffset.left="parentElement.offset().left;" elementoffset.top="parentElement.offset().top;" elements="" elementsize="{}," elementsize.height="parentElement.height();" elementsize.width="parentElement.width();" else="" empty="" even="" event="" execution="" figured="" firefox="" for="" function="" get="" haven't="" height:="" i="" i++)="" if="" if($element.css('display')="=" ignore="" important="" in="" insert="" interferred="" into="" inview="$element.data('inview')," is="" it="" items="" me="" move="" not="" null="" of="" onresize="" onscroll="" out="" parentelement="$element.parent();" place="" return;="" seems="" sometimes="" sounds="" suddenly="" sum="" that="" the="" this="" though="" to="" tree="" unset="" used="" values="" var="" viewportoffset="" viewportsize="" visiblepartsmerged;="" visiblepartx,="" visibleparty,="" weird:="" where="" why="" width:="" yet:="" {="" ||="" }="">= 0 &amp;&amp; element.offsetHeight &gt;= 0 &amp;&amp; element.style.display != "none" &amp;&amp;
            elementOffset.top + elementSize.height &gt; viewportOffset.top &amp;&amp;
            elementOffset.top &lt; viewportOffset.top + viewportSize.height &amp;&amp;
            elementOffset.left + elementSize.width &gt; viewportOffset.left &amp;&amp;
            elementOffset.left &lt; viewportOffset.left + viewportSize.width) {
          visiblePartX = (viewportOffset.left &gt; elementOffset.left ?
            'right' : (viewportOffset.left + viewportSize.width) &lt; (elementOffset.left + elementSize.width) ?
            'left' : 'both');
          visiblePartY = (viewportOffset.top &gt; elementOffset.top ?
            'bottom' : (viewportOffset.top + viewportSize.height) &lt; (elementOffset.top + elementSize.height) ?
            'top' : 'both');
          visiblePartsMerged = visiblePartX + "-" + visiblePartY;
          if (!inView || inView !== visiblePartsMerged) {
            $element.data('inview', visiblePartsMerged).trigger('inview', [true, visiblePartX, visiblePartY]);
          }
        } else if (inView) {
          $element.data('inview', false).trigger('inview', [false]);
        }
      }
    }
  }

  $(w).bind("scroll resize", function() {
    viewportSize = viewportOffset = null;
  });

  // IE &lt; 9 scrolls to focused elements without firing the "scroll" event
  if (!documentElement.addEventListener &amp;&amp; documentElement.attachEvent) {
    documentElement.attachEvent("onfocusin", function() {
      viewportOffset = null;
    });
  }

  // Use setInterval in order to also make sure this captures elements within
  // "overflow:scroll" elements or elements that appeared in the dom tree due to
  // dom manipulation and reflow
  // old: $(window).scroll(checkInView);
  //
  // By the way, iOS (iPad, iPhone, ...) seems to not execute, or at least delays
  // intervals while the user scrolls. Therefore the inview event might fire a bit late there
  setInterval(checkInView, 250);
})(jQuery);</elementslength;></body></html>