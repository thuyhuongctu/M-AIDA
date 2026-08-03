(function(){
  'use strict';
  var root=document.getElementById('intelligence');
  if(!root)return;
  var fallback={studies:236,effect_sizes:286,economies:35,cross_border_studies:42,pooled_r:.074,adjusted_r:.034,trim_fill_imputed:57,i2_percent:62.6,q:1902.40,q_df:285};
  var data=fallback;
  var lenses={
    geography:{title:['Evidence geography','Địa lý bằng chứng'],copy:['The evidence base is internationally distributed, but its density is uneven. Concentration is a design signal for future sampling—not proof that existing findings are invalid.','Bằng chứng có phạm vi quốc tế nhưng phân bố không đồng đều. Sự tập trung là tín hiệu để thiết kế mẫu tương lai, không phải bằng chứng rằng các kết quả hiện có không hợp lệ.'],value:function(d){return '70 / '+d.studies;},label:['East Asia studies','Nghiên cứu Đông Á'],note:['Approximately 29.7% of the locked corpus','Khoảng 29,7% kho dữ liệu đã khóa'],findings:[['35 located economies are represented.','Có 35 nền kinh tế được định vị.'],['42 cross-border studies are counted but not pinned.','42 nghiên cứu xuyên biên giới được tính nhưng không ghim trên bản đồ.'],['Use country coverage to target replication priorities.','Dùng độ phủ quốc gia để xác định ưu tiên nghiên cứu lặp lại.']],width:function(d){return 70/d.studies*100;},focus:'geo'},
    heterogeneity:{title:['Between-study dispersion','Phân tán giữa các nghiên cứu'],copy:['The pooled relationship varies materially across studies. This supports moderator analysis and careful interpretation of context rather than a single universal claim.','Mối quan hệ gộp thay đổi đáng kể giữa các nghiên cứu. Điều này ủng hộ phân tích biến điều tiết và diễn giải thận trọng theo bối cảnh thay vì một kết luận phổ quát.'],value:function(d){return d.i2_percent.toFixed(1)+'%';},label:['I² heterogeneity','I² dị biệt'],note:function(d){return ['Q = '+d.q.toFixed(2)+'; df = '+d.q_df,'Q = '+d.q.toFixed(2)+'; df = '+d.q_df];},findings:[['I² describes dispersion; it is not a pass/fail test.','I² mô tả độ phân tán; không phải phép thử đạt/không đạt.'],['Moderator patterns should be pre-specified where possible.','Nên xác định trước các biến điều tiết khi có thể.'],['Contextual variation is a research opportunity.','Biến thiên theo bối cảnh là một cơ hội nghiên cứu.']],width:function(d){return d.i2_percent;},focus:'method'},
    bias:{title:['Publication-bias sensitivity','Độ nhạy với thiên lệch công bố'],copy:['The adjusted estimate is smaller than the baseline estimate. It is reported as a sensitivity analysis—not as a corrected or uniquely true effect.','Ước lượng điều chỉnh nhỏ hơn ước lượng cơ sở. Kết quả này được báo cáo như một phân tích độ nhạy, không phải hiệu ứng đã “sửa đúng” hay chân lý duy nhất.'],value:function(d){return d.pooled_r.toFixed(3)+' → '+d.adjusted_r.toFixed(3);},label:['Baseline to adjusted r','r cơ sở đến điều chỉnh'],note:function(d){return [d.trim_fill_imputed+' trim-and-fill studies imputed','Nội suy '+d.trim_fill_imputed+' nghiên cứu bằng trim-and-fill'];},findings:[['Baseline pooled r remains the primary registered result.','r gộp cơ sở vẫn là kết quả đăng ký chính.'],['The adjusted estimate tests robustness to asymmetry.','Ước lượng điều chỉnh kiểm tra độ bền trước bất đối xứng.'],['Report both estimates with their assumptions.','Báo cáo cả hai ước lượng cùng các giả định.']],width:function(d){return d.adjusted_r/d.pooled_r*100;},focus:'method'},
    governance:{title:['Human-governed evidence','Bằng chứng do con người quản trị'],copy:['Every record used in the analysis crossed a human verification and immutable-lock boundary. M-AIDA assists extraction; researchers retain responsibility for inclusion and interpretation.','Mỗi bản ghi được phân tích đều vượt qua ranh giới kiểm chứng của con người và khóa bất biến. M-AIDA hỗ trợ trích xuất; nhà nghiên cứu vẫn chịu trách nhiệm về lựa chọn và diễn giải.'],value:function(){return '100%';},label:['Analyzed records locked','Bản ghi phân tích đã khóa'],note:['AI-assisted, human-verified workflow','Quy trình AI hỗ trợ, con người kiểm chứng'],findings:[['Unlocked records cannot enter controlled export.','Bản ghi chưa khóa không thể đi vào kết xuất kiểm soát.'],['Decision provenance is retained at record level.','Nguồn gốc quyết định được lưu ở cấp bản ghi.'],['Reproducible data remain linked to the analysis version.','Dữ liệu tái lập được liên kết với phiên bản phân tích.']],width:function(){return 100;},focus:'cross'}
  };
  function lang(){return (document.documentElement.lang||'en').toLowerCase().indexOf('vi')===0?1:0;}
  function pair(v){return Array.isArray(v)?v[lang()]:v(data)[lang()];}
  function render(key){
    var lens=lenses[key]||lenses.geography;
    root.setAttribute('data-lens',key);
    root.querySelectorAll('.ri-tab').forEach(function(btn){btn.setAttribute('aria-selected',String(btn.getAttribute('data-lens')===key));});
    root.querySelector('[data-ri="title"]').textContent=pair(lens.title);
    root.querySelector('[data-ri="copy"]').textContent=pair(lens.copy);
    root.querySelector('[data-ri="value"]').textContent=lens.value(data);
    root.querySelector('[data-ri="label"]').textContent=pair(lens.label);
    root.querySelector('[data-ri="note"]').textContent=pair(lens.note);
    root.querySelector('[data-ri="bar"]').style.width=Math.max(2,Math.min(100,lens.width(data)))+'%';
    var list=root.querySelector('[data-ri="findings"]');list.innerHTML='';
    lens.findings.forEach(function(f){var li=document.createElement('li');li.textContent=f[lang()];list.appendChild(li);});
    root.querySelectorAll('.ri-callout').forEach(function(el){var active=el.getAttribute('data-callout')===lens.focus;el.classList.toggle('is-focus',active);el.classList.toggle('is-dim',!active);});
  }
  function metrics(d){
    [['studies',d.studies],['effects',d.effect_sizes],['economies',d.economies],['cross',d.cross_border_studies]].forEach(function(item){var el=root.querySelector('[data-metric="'+item[0]+'"]');if(el)el.textContent=item[1];});
  }
  root.querySelectorAll('.ri-tab').forEach(function(btn){btn.addEventListener('click',function(){render(btn.getAttribute('data-lens'));});});
  fetch('assets/data/site-metrics.json').then(function(r){if(!r.ok)throw new Error('metrics');return r.json();}).then(function(json){data=Object.assign({},fallback,json);metrics(data);render(root.getAttribute('data-lens')||'geography');}).catch(function(){metrics(data);render('geography');});
  new MutationObserver(function(){render(root.getAttribute('data-lens')||'geography');}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  metrics(data);render('geography');
})();
