

frappe.ui.form.on('Monthly Allocation', {
	refresh(frm) {
	    var startDate = 0 || frm.doc.from ;
        
	},
	before_save:function(frm){
        let allocation_details = frm.doc.allocation_details;
        // var days = days_dates;
        var todayDate = frm.doc.from;
        var endDate = frm.doc.to;
        var obj = {
            0:"Sunday",
            1:"Monday",
            2:"Tuesday",
            3:"Wednesday",
            4:"Thursday",
            5:"Friday",
            6:"Saturday"
        }
        allocation_details.forEach(row => {
            var week_days = [];
            week_days.push(row.sunday,row.monday,row.tuesday,row.wednesday,row.thursday,row.friday,row.saturday);

            for(let j=0;j<week_days.length;j++){
                for(let key in obj){
                   
                    if(key == j){
                       
                        sanitize(row.employee,todayDate,endDate,obj[key],week_days[j]);
                    }
                }
      
                    
            }
        });
	
	    
	},
	to:function(frm,cdt,cdn){
        var d = locals[cdt][cdn];
        var startDate = d.from;
        var endDatee = d.to;

    }
});




function get_dates_from_to (startDate, endDate) {
            let days_with_dates = []
            let current = new Date(startDate);
            let end = new Date(endDate);
            let dates = [];
            var Year = 0||startDate.split('')[0] + startDate.split('')[1] + startDate.split('')[2] + startDate.split('')[3]+ '-';
            var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday'];
            
             
            let tempDate = new Date(current.getTime());
            while(tempDate <= end){
              dates.push(new Date(tempDate));
              tempDate.setDate(tempDate.getDate() + 1);
            }
            
            
            for(let i =0;i<dates.length;i++){
                var obj= {};
                var day = days[dates[i].getDay()].toString();
                var date =  dates[i].getDate() ;
                var month = (dates[i].getMonth() +1 )+ '-';
                var full_date = Year+month+date;
                obj[day] = full_date;
                // console.log(obj);
                days_with_dates.push(obj);
                
            }
           
            return days_with_dates;
        }
        
        
        
        
        
function inser_doc(shift_type,datestr,employee,todayDate){
    // console.log(shift_type);
    if(shift_type != 'off-day'){
        console.log(typeof(datestr) + datestr);
        let date = new Date(datestr)
        date.setDate(date.getDate()+1);
        let newDate = `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`;
        console.log(newDate)
        frappe.db.insert({
            doctype: 'Shift Assignment',
            employee: employee,
            // start: date,
            start_date: datestr,
            end_date: newDate,
            shift_type: shift_type, 
            
        }).then((responce)=>{
            console.log('New shif assignment added: '+responce.name);
        }).catch((error)=>{
            console.log('error: '+error)
        });
       
    }
    if(shift_type == 'off-day'){
        frappe.db.insert({
            doctype: 'Attendance',
            employee: employee,
            attendance_date: datestr,
            status:"Day Off"
        }).then((responce)=>{
            console.log('New Attendance added: '+responce.name);
        }).catch((error)=>{
            console.log('error: '+error)
        });
    }
 }
 
 
 function sanitize(employee,todayDate,endDate,day,week_day){
        var dayes = get_dates_from_to(todayDate,endDate);
         for(let d=0;d<dayes.length;d++){
                var day_date = "";
                var shift_type="";
                        try{
                            if(Object.keys(dayes[d])[0] == day){
                                 day_date = Object.values(dayes[d])[0];
                                 console.log(Object.keys(dayes[d])[0]);
                                 shift_type = week_day;
                                
                                inser_doc(shift_type,day_date,employee,todayDate);
                             
                            }
                            }catch(e){
                                console.log(e.message);
                            }
                    }
 }





 //////////// Client Script For Day in Attendance and Shift Assignment //////
 // ATTENDANCE //
 frappe.ui.form.on('Attendance', {
	refresh(frm) {
		
	},
	before_save:function(frm,cdt,cdn){
	    var d = locals[cdt][cdn];
	    var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday'];
	    let current_date = new Date(frm.doc.attendance_date);
	    var day = days[current_date.getDay()];
	    console.log(day);
	    console.log(current_date);
	    d.attendance_day = day;
	    frm.refresh_field("attendance_day");
	}
});
 // end ATTENDANCE //


  // Employee Checkin //
  frappe.ui.form.on('Employee Checkin', {
	refresh(frm) {
		
	},
	before_save:function(frm,cdt,cdn){
	    var d = locals[cdt][cdn];
	    var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday'];
	    let current_date = new Date(frm.doc.time);
	    var day = days[current_date.getDay()];
	    console.log(day);
	    console.log(current_date);
	    d.day_ = day;
	    frm.refresh_field("day_");
	}
});
 // end Employee Checkin  //
