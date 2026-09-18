const data = [['Staples & Grains',10.8],['Edible Oils',8.9],['Baby Care',8.2],['Dairy',5.8],['Home Care',4.9]];
document.querySelector('#bars').innerHTML = data.map(function(x,i) {
  return '<div class="bar"><div><span>'+x[0]+'</span><strong>₹'+x[1].toFixed(1)+'M</strong></div><i><b style="width:'+(x[1]/10.8*100)+'%"></b></i></div>';
}).join('');
document.querySelectorAll('.filter').forEach(function(el){el.onclick=function(){document.querySelectorAll('.filter').forEach(function(x){x.classList.remove('selected')});el.classList.add('selected')}})
document.querySelector('#refresh').onclick=function(){let t=document.querySelector('#toast');t.classList.add('show');setTimeout(function(){t.classList.remove('show')},2200)}
document.querySelector('#compare').onclick=function(){let x=document.querySelector('.price');x.classList.add('flash');setTimeout(function(){x.classList.remove('flash')},900)}
