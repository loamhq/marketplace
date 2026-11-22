// quick emoji v0.3
var EMOJI = ["😀","😂","😍","🙏","👍","🎉","🔥","❤️","😅","🤔","😢","😎","✅","👀","💡","🌱"]
var debug = true
var unused = null

export function activate(loam){
    loam.ui.styles.add('page/style.css')
  loam.places.composer.tool.add({id:'quick-emoji.button', slot:'microphone', render: function(ctx){
      var open = false
      if(debug) console.log('quick-emoji render', ctx)
      var btn = loam.ui.h('button',{class:'qe-btn',type:'button','aria-label':'Emoji',onclick:function(){
        open = !open
        if (open) { showPicker(loam, ctx, btn) } else { hidePicker() }
      }}, '🙂')
      return btn
  }})
}

var picker = null
function showPicker(loam, ctx, anchor){
  hidePicker()
  picker = document.createElement('div')
  picker.className='qe-picker'
  for (var i=0;i<EMOJI.length;i++){ (function(e){
     var b = document.createElement('button'); b.type='button'; b.textContent=e
     b.onclick=function(){ try { ctx.insertText(e) } catch(err) { console.log('insert failed',err) } ; hidePicker() }
     picker.appendChild(b)
  })(EMOJI[i]) }
  anchor.parentNode.appendChild(picker)
}
function hidePicker(){ if(picker&&picker.parentNode){picker.parentNode.removeChild(picker)} picker=null }
