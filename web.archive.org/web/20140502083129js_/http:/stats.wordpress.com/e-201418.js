var _____WB$wombat$assign$function_____ = function(name) {return (self._wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init(name)) || self[name]; };
if (!self.__WB_pmw) { self.__WB_pmw = function(obj) { this.__WB_source = obj; return this; } }
{
  let window = _____WB$wombat$assign$function_____("window");
  let self = _____WB$wombat$assign$function_____("self");
  let document = _____WB$wombat$assign$function_____("document");
  let location = _____WB$wombat$assign$function_____("location");
  let top = _____WB$wombat$assign$function_____("top");
  let parent = _____WB$wombat$assign$function_____("parent");
  let frames = _____WB$wombat$assign$function_____("frames");
  let opener = _____WB$wombat$assign$function_____("opener");

function st_go(a){var i,u=document.location.protocol+'//web.archive.org/web/20140502083509/http://stats.wordpress.com/g.gif?host='+escape(document.location.host)+'&rand='+Math.random();for(i in a){u=u+'&'+i+'='+escape(a[i]);}u=u+'&ref='+escape(document.referrer);document.open();document.write("<img id=\"wpstats\" src=\""+u+"\" alt=\"\" />");document.close();}
function wpcomAddEvent(el,ev,fn){var isIE=window.attachEvent?true:false;if(isIE)el.attachEvent('on'+ev,fn);else if(el.addEventListener)el.addEventListener(ev,fn,false);}
function linkmousedown(event){var isIE=window.attachEvent?true:false;event=event?event:(window.event?window.event:"");var m=isIE?window.event.srcElement:event.currentTarget;m.modo=true;}
function linkmouseout(event){var isIE=window.attachEvent?true:false;event=event?event:(window.event?window.event:"");var m=isIE?window.event.srcElement:event.currentTarget;m.modo=false;}
function linkmouseup(event){var isIE=window.attachEvent?true:false;event=event?event:(window.event?window.event:"");var m=isIE?window.event.srcElement:event.currentTarget;if(m.modo)linktracker_record(event);}
function linkclick(event){var isIE=window.attachEvent?true:false;event=event?event:(window.event?window.event:"");linktracker_record(event);}
function linktracker_init(b,p){_blog=b;_post=p;if(typeof document.location.host!='undefined')
var localserver=document.location.host;else
var localserver=document.location.toString().replace(/^[^\/]*\/+([^\/]*)(\/.*)?/,'$1');var els=document.getElementsByTagName('a');for(var i=0;i<els.length;i++){var href=els[i].href;if(href.match(eval('/^(http(s)?:\\/\\/)?'+localserver+'/')))continue;if(href.match(eval('/^javascript/')))continue;wpcomAddEvent(els[i],'mousedown',linkmousedown);wpcomAddEvent(els[i],'mouseout',linkmouseout);wpcomAddEvent(els[i],'mouseup',linkmouseup);}}
function linktracker_record(event){var isIE=window.attachEvent?true:false;event=event?event:(window.event?window.event:"");var b=isIE?window.event.srcElement:event.currentTarget;while(b.nodeName!="A"){if(typeof b.parentNode=='undefined')return;b=b.parentNode;}
var bh=b.href;var pr=document.location.protocol||'http:';var b=(typeof _blog!='undefined')?_blog:0;var p=(typeof _post!='undefined')?_post:0;var i=new Image(1,1);i.src=pr+'//web.archive.org/web/20140502083509/http://stats.wordpress.com/c.gif?s=2&b='+b+'&p='+p+'&u='+escape(bh);i.onLoad=function(){cmcVoid();}}
function cmcVoid(){return;}

}
/*
     FILE ARCHIVED ON 08:35:09 May 02, 2014 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 23:05:26 Sep 18, 2025.
     JAVASCRIPT APPENDED BY WAYBACK MACHINE, COPYRIGHT INTERNET ARCHIVE.

     ALL OTHER CONTENT MAY ALSO BE PROTECTED BY COPYRIGHT (17 U.S.C.
     SECTION 108(a)(3)).
*/
/*
playback timings (ms):
  captures_list: 0.761
  exclusion.robots: 0.031
  exclusion.robots.policy: 0.013
  esindex: 0.015
  cdx.remote: 32.056
  LoadShardBlock: 168.659 (3)
  PetaboxLoader3.datanode: 236.611 (4)
  load_resource: 216.638
  PetaboxLoader3.resolve: 76.558
*/