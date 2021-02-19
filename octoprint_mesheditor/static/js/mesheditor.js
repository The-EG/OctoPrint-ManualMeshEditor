$(function() {
    function MeshEditorViewModel(parameters) {
        var self = this;

        self.pointValue = ko.observable(0.0);
        self.row = ko.observable(0);
        self.col = ko.observable(0);

        self.settings = parameters[0];
        self.printerState = parameters[1];

        self.selectPoint = function(event) {
            var col = parseInt($(event.target).attr('data-col'));
            var row = parseInt($(event.target).attr('data-row'));
            var val = parseFloat($(event.target).text());
            self.row(row);
            self.col(col);
            self.pointValue(val);
            $('#mesh_editor_save_val_btn').prop('disabled', false);
            $('#mesh_editor_move_to_btn').prop('disabled', false);
        }


        self.updateMesh = function() {
            $('#mesh_editor_get_mesh').prop('disabled',true);
            $('#mesh_editor_save_eeprom').prop('disabled',true);
            self.pointValue('');
            self.row('');
            self.col('');
            $('#mesh_editor_save_val_btn').prop('disabled',true);
            $('#mesh_editor_move_to_btn').prop('disabled',true);
            OctoPrint.control.sendGcode("G29 S0");
        }

        self.saveToEEPROM = function() { OctoPrint.control.sendGcode("M500"); }

        self.savePoint = function() {
            OctoPrint.control.sendGcode(`G29 S3 I${self.col()} J${self.row()} Z${self.pointValue()}`);
            self.updateMesh();
        }

        self.moveToPoint = function() {
            var bedW = parseFloat(self.settings.settings.plugins.mesheditor.move_bed_width());
            var bedL = parseFloat(self.settings.settings.plugins.mesheditor.move_bed_length());
            var zHop = parseFloat(self.settings.settings.plugins.mesheditor.move_z_hop());
            var mms = parseFloat(self.settings.settings.plugins.mesheditor.move_speed_mms());
            var offX = parseFloat(self.settings.settings.plugins.mesheditor.move_offset_x());
            var offY = parseFloat(self.settings.settings.plugins.mesheditor.move_offset_y());
            var gridPoints = parseFloat(self.settings.settings.plugins.mesheditor.grid_size());
            var inset = parseFloat(self.settings.settings.plugins.mesheditor.move_mesh_inset());
            var speed = mms * 60;

            var c = self.col();
            var r = gridPoints - 1 - self.row();

            var x = (((bedW - (inset * 2)) / (gridPoints - 1)) * c) + offX + inset;
            var y = (((bedL - (inset * 2)) / (gridPoints - 1)) * r) + offY + inset;

            if (y > bedL) y = bedL;
            if (x > bedW) x = bedW;

            OctoPrint.control.sendGcode([
                `G0 Z${zHop} F${speed}`,
                `G0 X${x} Y${y} F${speed}`,
                `G0 Z0 F${speed}`,
            ]);
        }
        
        self.onEventplugin_mesheditor_mesh_ready = function(payload) {
            var data = payload;
            var grid_size = self.settings.settings.plugins.mesheditor.grid_size();
            if (data.result == 'ok') {
                grid_size = data.grid_size;
            }

            $("#mesheditor_mesh_grid").empty();
     
            var tbl = $('<table class="mesh_grid" />').appendTo("#mesheditor_mesh_grid");         
            var hdr = $('<tr />');
            hdr.append($('<td>&nbsp;</td>'));
            for (var col = 0; col < grid_size; col ++) {
                hdr.append($(`<th>${col}</th>`));
            }
            tbl.append(hdr);
            for (var row = 0; row < grid_size; row++) {
                

                var tr = $("<tr />");
                tbl.append(tr);
                tr.append($(`<th>${row}</th>`));
                for (var col = 0; col < grid_size; col++) {
                    var  btn = $('<button class="btn mesh_button" />');
                    if (data.result=='ok') btn.text(data.data[row][col].toFixed(3));
                    else btn.text((0.000).toFixed(3));
                    btn.attr({'data-col': col, 'data-row': row});
                    btn.click(self.selectPoint)
                    var td = $('<td />');
                    td.append(btn);
                    tr.append(td);
                }
            }
            $('#mesh_editor_save_val_btn').prop('disabled', true);
            $('#mesh_editor_move_to_btn').prop('disabled', true);
            self.row('');
            self.col('');
            self.pointValue('');
            $('#mesh_editor_get_mesh').prop('disabled',false);
            $('#mesh_editor_save_eeprom').prop('disabled',false);
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: MeshEditorViewModel,
        dependencies: ["settingsViewModel","printerStateViewModel"],
        elements: ["#tab_plugin_mesheditor"]
    });
});