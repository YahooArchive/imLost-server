/**
 * Created with PyCharm.
 * User: young
 * Date: 6/23/13
 * Time: 10:37 AM
 * To change this template use File | Settings | File Templates.
 */

db.users.ensureIndex({user_id:1}, {unique: true});
db.users.ensureIndex({user_id:1, password:1}, {unique: true});
db.users.ensureIndex({access_token:1}, {unique: true, sparse:true});
