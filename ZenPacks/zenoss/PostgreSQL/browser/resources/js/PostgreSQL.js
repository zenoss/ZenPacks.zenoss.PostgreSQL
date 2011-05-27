(function(){

var ZC = Ext.ns('Zenoss.component');

/*
 * Friendly names for the components.
 */
ZC.registerName('PostgreSQLDatabase', _t('Database'), _t('Databases'));
ZC.registerName('PostgreSQLTable', _t('Table'), _t('Tables'));

/*
 * Register types so jumpToEntity will work.
 */

// The DeviceClass matcher got too greedy in 3.1.x branch. Throttling it.
Zenoss.types.TYPES.DeviceClass[0] = new RegExp(
    "^/zport/dmd/Devices(/(?!devices)[^/*])*/?$");

Zenoss.types.register({
    'PostgreSQLDatabase':
        "^/zport/dmd/Devices.*/devices/.*/pgDatabases/[^/]*/?$",
    'PostgreSQLTable':
        "^/zport/dmd/Devices.*/devices/.*/pgDatabases/.*/tables/[^/]*/?$"
});

/*
 * Endpoint-local custom renderers.
 */
Ext.apply(Zenoss.render, {    
    entityLinkFromGrid: function(obj) {
        if (obj && obj.uid && obj.name) {
            if ( !this.panel || this.panel.subComponentGridPanel) {
                return String.format(
                    '<a href="javascript:Ext.getCmp(\'component_card\').componentgrid.jumpToEntity(\'{0}\', \'{1}\');">{1}</a>',
                    obj.uid, obj.name);
            } else {
                return obj.name;
            }
        }
    }
});

/*
 * Generic ComponentGridPanel
 */
ZC.PostgreSQLComponentGridPanel = Ext.extend(ZC.ComponentGridPanel, {
    subComponentGridPanel: false,
    
    jumpToEntity: function(uid, name) {
        var tree = Ext.getCmp('deviceDetailNav').treepanel,
            sm = tree.getSelectionModel(),
            compsNode = tree.getRootNode().findChildBy(function(n){
                return n.text=='Components';
            });
    
        var compType = Zenoss.types.type(uid);
        var componentCard = Ext.getCmp('component_card');
        componentCard.setContext(compsNode.id, compType);
        componentCard.selectByToken(uid);
        sm.suspendEvents();
        compsNode.findChildBy(function(n){return n.id==compType;}).select();
        sm.resumeEvents();
    }
});

/*
 * Database ComponentGridPanel
 */
ZC.PostgreSQLDatabasePanel = Ext.extend(ZC.PostgreSQLComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'entity',
            componentType: 'PostgreSQLDatabase',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'severity'},
                {name: 'entity'},
                {name: 'dbSize'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                sortable: true,
                width: 50
            },{
                id: 'entity',
                dataIndex: 'entity',
                header: _t('Name'),
                renderer: Zenoss.render.entityLinkFromGrid,
                panel: this
            },{
                id: 'dbSize',
                dataIndex: 'dbSize',
                header: _t('Size'),
                renderer: Zenoss.render.memory,
                sortable: true,
                width: 70
            },{
                id: 'tableCount',
                dataIndex: 'tableCount',
                header: _t('# Tables'),
                sortable: true,
                width: 60
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                sortable: true,
                width: 65
            }]
        });
        ZC.PostgreSQLDatabasePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('PostgreSQLDatabasePanel', ZC.PostgreSQLDatabasePanel);

/*
 * Table ComponentGridPanel
 */
ZC.PostgreSQLTablePanel = Ext.extend(ZC.PostgreSQLComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'entity',
            componentType: 'PostgreSQLTable',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'severity'},
                {name: 'entity'},
                {name: 'tableSchema'},
                {name: 'tableSize'},
                {name: 'totalTableSize'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                sortable: true,
                width: 50
            },{
                id: 'entity',
                dataIndex: 'entity',
                header: _t('Name'),
                renderer: Zenoss.render.entityLinkFromGrid,
                panel: this
            },{
                id: 'tableSchema',
                dataIndex: 'tableSchema',
                header: _t('Schema'),
                sortable: true,
                width: 80
            },{
                id: 'tableSize',
                dataIndex: 'tableSize',
                header: _t('Size'),
                renderer: Zenoss.render.memory,
                sortable: true,
                width: 60
            },{
                id: 'totalTableSize',
                dataIndex: 'totalTableSize',
                header: _t('Total Size'),
                renderer: Zenoss.render.memory,
                sortable: true,
                width: 75
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                sortable: true,
                width: 65
            }]
        });
        ZC.PostgreSQLTablePanel.superclass.constructor.call(this, config);
    }
});

Ext.reg('PostgreSQLTablePanel', ZC.PostgreSQLTablePanel);

/*
 * Custom Component Views
 */
Zenoss.nav.appendTo('Component', [{
    id: 'component_pg_tables',
    text: _t('Tables'),
    xtype: 'PostgreSQLTablePanel',
    subComponentGridPanel: true,
    filterNav: function(navpanel) {
        if (navpanel.refOwner.componentType == 'PostgreSQLDatabase') {
            return true;
        } else {
            return false;
        }
    },
    setContext: function(uid) {
        ZC.PostgreSQLTablePanel.superclass.setContext.apply(this, [uid]);
    }
}]);

})();

