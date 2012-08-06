(function(){

var ZC = Ext.ns('Zenoss.component');

/*
 * Friendly names for the components.
 */
ZC.registerName('PostgreSQLDatabase', _t('Database'), _t('Databases'));
ZC.registerName('PostgreSQLTable', _t('Table'), _t('Tables'));

/*
 * Endpoint-local custom renderers.
 */
Ext.apply(Zenoss.render, {
    PostgreSQL_entityLinkFromGrid: function(obj, col, record) {
        if (!obj)
            return;

        if (typeof(obj) == 'string')
            obj = record.data;

        if (!obj.title && obj.name)
            obj.title = obj.name;

        var isLink = false;

        if (this.refName == 'componentgrid') {
            // Zenoss >= 4.2 / ExtJS4
            if (this.subComponentGridPanel || this.componentType != obj.meta_type)
                isLink = true;
        } else {
            // Zenoss < 4.2 / ExtJS3
            if (!this.panel || this.panel.subComponentGridPanel)
                isLink = true;
        }

        if (isLink) {
            return '<a href="javascript:Ext.getCmp(\'component_card\').componentgrid.jumpToEntity(\''+obj.uid+'\', \''+obj.meta_type+'\');">'+obj.title+'</a>';
        } else {
            return obj.title;
        }
    }
});

/*
 * Generic ComponentGridPanel
 */
ZC.PostgreSQLComponentGridPanel = Ext.extend(ZC.ComponentGridPanel, {
    subComponentGridPanel: false,

    jumpToEntity: function(uid, meta_type) {
        var tree = Ext.getCmp('deviceDetailNav').treepanel;
        var tree_selection_model = tree.getSelectionModel();
        var components_node = tree.getRootNode().findChildBy(
            function(n) {
                if (n.data) {
                    // Zenoss >= 4.2 / ExtJS4
                    return n.data.text == 'Components';
                }

                // Zenoss < 4.2 / ExtJS3
                return n.text == 'Components';
            });

        // Reset context of component card.
        var component_card = Ext.getCmp('component_card');

        if (components_node.data) {
            // Zenoss >= 4.2 / ExtJS4
            component_card.setContext(components_node.data.id, meta_type);
        } else {
            // Zenoss < 4.2 / ExtJS3
            component_card.setContext(components_node.id, meta_type);
        }

        // Select chosen row in component grid.
        component_card.selectByToken(uid);

        // Select chosen component type from tree.
        var component_type_node = components_node.findChildBy(
            function(n) {
                if (n.data) {
                    // Zenoss >= 4.2 / ExtJS4
                    return n.data.id == meta_type;
                }

                // Zenoss < 4.2 / ExtJS3
                return n.id == meta_type;
            });

        if (component_type_node.select) {
            tree_selection_model.suspendEvents();
            component_type_node.select();
            tree_selection_model.resumeEvents();
        } else {
            tree_selection_model.select([component_type_node], false, true);
        }
    }
});

/*
 * Database ComponentGridPanel
 */
ZC.PostgreSQLDatabasePanel = Ext.extend(ZC.PostgreSQLComponentGridPanel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'name',
            componentType: 'PostgreSQLDatabase',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'meta_type'},
                {name: 'severity'},
                {name: 'dbSize'},
                {name: 'tableCount'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                sortable: true,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                renderer: Zenoss.render.PostgreSQL_entityLinkFromGrid,
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
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons,
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
            autoExpandColumn: 'name',
            componentType: 'PostgreSQLTable',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'meta_type'},
                {name: 'severity'},
                {name: 'database'},
                {name: 'tableSchema'},
                {name: 'tableSize'},
                {name: 'totalTableSize'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                sortable: true,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                renderer: Zenoss.render.PostgreSQL_entityLinkFromGrid,
                panel: this
            },{
                id: 'database',
                dataIndex: 'database',
                header: _t('Database'),
                renderer: Zenoss.render.PostgreSQL_entityLinkFromGrid,
                width: 80
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
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons,
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

