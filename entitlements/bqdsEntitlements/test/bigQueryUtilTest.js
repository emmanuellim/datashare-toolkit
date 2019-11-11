/**
 * Copyright 2019, Google, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* eslint-disable promise/always-return */
/* eslint-disable promise/catch-or-return */

const { argv, uuidv4 } = require('./testSetup');

const assert = require('assert');
const chai = require('chai'), expect = chai.expect, should = chai.should();
const chaiAsPromised = require('chai-as-promised');
chai.use(chaiAsPromised);

const bigqueryUtil = require("../bigqueryUtil");

if (argv.runCloudTests) {
    bigqueryUtil.init(argv.projectId);

    it("execute query", async () => {
        const options = { query: "select 1 union all select 2" };
        const [rows] = await bigqueryUtil.executeQuery(options);
        expect(rows.length).is.equal(2);
    });

    it("query should be valid", async () => {
        const query = "select 1 union all select 2";
        return expect(bigqueryUtil.validateQuery(query)).to.eventually.be.true;
    });

    it("query should be invalid", async () => {
        const query = "Xselect 1";
        return expect(bigqueryUtil.validateQuery(query)).to.eventually.be.false;
    });

    it("query should be valid with limit", async () => {
        const query = "select 1 union all select 2 limit 10";
        return expect(bigqueryUtil.validateQuery(query)).to.eventually.be.true;
    });

    it("query should be invalid with limit", async () => {
        const query = "Xselect 1 limit 10";
        return expect(bigqueryUtil.validateQuery(query)).to.eventually.be.false;
    });

    const uuid = uuidv4().replace(/-/g, "_");
    const viewName = `v_${uuid}`;

    it("create dataset, table, view, check for existence, and delete", async () => {
        await bigqueryUtil.createDataset(uuid).then((result => {
            expect(result, "created dataset").is.true;
        })).then(() => {
            return bigqueryUtil.datasetExists(uuid);
        }).then((result) => {
            expect(result).is.true;
        }).then(() => {
            const schema = [{
                "name": "column1",
                "type": "STRING",
                "mode": "REQUIRED"
            },
            {
                "name": "column2",
                "type": "STRING",
                "mode": "REQUIRED"
            }];
            return bigqueryUtil.createTable(uuid, uuid, schema);
        }).then((result) => {
            expect(result).is.true;
        }).then(() => {
            return bigqueryUtil.tableColumns(uuid, uuid);
        }).then((columns) => {
            expect(columns).length.is(2);
            expect(columns[0]).is.equal("column1");
            expect(columns[1]).is.equal("column2");
        }).then(() => {
            const query = `select * from \`${argv.projectId}.${uuid}.${uuid}\``;
            return bigqueryUtil.createView(argv.projectId, uuid, viewName, query);
        }).then((result) => {
            return bigqueryUtil.viewExists(argv.projectId, uuid, viewName);
        }).then((result) => {
            expect(result).is.true;
        }).then(() => {
            return bigqueryUtil.deleteTable(uuid, viewName);
        }).then((result) => {
            expect(result).is.true;
        }).then(() => {
            return bigqueryUtil.deleteTable(uuid, uuid);
        }).then((result) => {
            expect(result).is.true;
        }).then(() => {
            return bigqueryUtil.deleteDataset(uuid);
        }).then((result) => {
            expect(result).is.true;
        }).catch((reason) => {
            expect.fail(`Failed: ${reason}`);
        });
    });
}