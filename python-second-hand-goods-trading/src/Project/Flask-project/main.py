from flask import Flask,render_template,url_for,request,redirect,session,g
import config
from extensions import db
from models import User,Item,Comment,Interest
from decorators import login_required
from sqlalchemy.sql import  text
import os
from werkzeug.security import generate_password_hash

UPLOAD_PATH = r'F:\张越\二手项目交易平台flask项目\python-second-hand-goods-trading\src\源程序\程序代码\static\images'

def allowfiletype(filename):
    type = filename.split('.')[-1]
    if type in ['png','jpg','bmp','gif']:
        return True
    else:
        return False

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)




##首页,展示所有发布了的物品
@app.route('/')
def index():
    items = {
        'items' : Item.query.filter(Item.isclosed==0).order_by(text('-create_time')).all(),
    }
    return render_template('index.html',**items)

##登录
@app.route('/login/',methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html',somethingwrong=False)
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter(User.username==username).first()

        ##用户已经注册
        if user and user.checkPassWord(password):
            session['user_id'] = user.id
            session.permanent = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html',somethingwrong=True)

##注销
@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('login'))

##注册
@app.route('/regist/',methods=['GET','POST'])
def regist():
    if request.method == 'GET':
        return render_template('register.html',user_exist=False,password_not_checked=False)
    else:
        email = request.form.get('email')
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        rootuser = True if username=='root' else False
        #user=False
        user = User.query.filter(User.username==username).first()
        if user:
            return render_template('register.html',user_exist=True,password_not_checked=False)
        else:
            if password1!=password2:
                return render_template('register.html',user_exist=False,password_not_checked=True)
            else:
                new_user = User(username=username,email=email,password=password1,authority=rootuser)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))

##发布交易
@app.route('/release/',methods=['GET','POST'])
@login_required
def release():
    if request.method == 'GET':
        return render_template('realease_item.html')
    else:
        name = request.form.get('item_name')
        description = request.form.get('item_description')
        price = request.form.get('item_price')
        file = request.files.get('file')
        if file:
            img_name = file.filename
            if allowfiletype(img_name):
                imgurl = os.path.join(UPLOAD_PATH,img_name)
                file.save(imgurl)
            else:
                imgurl = None
        else:
            imgurl = None
        print(imgurl)
        item = Item(name=name,description=description,price=price,imgpath=imgurl)
        userid = session.get('user_id')
        item.owner = User.query.filter(User.id==userid).first()
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('index'))

##物品详情及评论页面
@app.route('/detail/<itemid>/')
@login_required
def detail(itemid):
    user = User.query.filter(User.id==session.get('user_id')).first()
    root_user = True if user.authority else False
    item = Item.query.filter(Item.id==itemid).first()
    if item.imgpath:
        item_img_name = item.imgpath.split('\\')[-1]
    else:
        item_img_name = ''
    imgpath = url_for('static',filename='images/{}'.format(item_img_name))
    inter = Interest.query.filter(Interest.userid==session.get('user_id'),Interest.itemid==itemid).first()
    if inter:
        flag = True
    else:
        flag = False
    contents = {
        'item_id':item.id,
        'item_name':item.name,
        'item_price':item.price,
        'item_description':item.description,
        'item_owner':item.owner.username,
        'item_createtime':item.create_time,
        'item_imgpath':imgpath,
        'comments':item.comments,
        'owner_email':item.owner.email,
        'flag':flag,
        'rootuser':root_user,
    }
    return render_template('item_detail.html',**contents)

##在特定物品评论区添加评论
@app.route('/add_comment/',methods=['POST'])
@login_required
def add_comment():
    content = request.form.get('content')
    comment = Comment(content=content)
    ownerid = session.get('user_id')
    user = User.query.filter(User.id==ownerid).first()
    comment.owner = user
    itemid = request.form.get('item-id')
    item = Item.query.filter(Item.id==itemid).first()
    comment.item = item
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('detail',itemid=itemid))

##搜索
@app.route('/search/')
@login_required
def search():
    q = request.args.get('q')
    if q:
        items = Item.query.filter(Item.name.contains(q)).order_by(text('-create_time')).all()
    else:
        items = Item.query.order_by(text('-create_time')).all()
    return render_template('index.html',items=items)

##个人中心
@app.route('/usercenter/<target>/')
def usercenter(target):
    print(target)
    userid = session.get('user_id')
    user = User.query.filter(User.id==userid).first()
    items = user.items
    if target == 'items':
        print('target is items')
        return render_template('usercenter.html',type='item',items=items,flag=1)
    elif target=='profile':
        print('target is profile')
        ##找出用户所有感兴趣的物品
        inters = Interest.query.filter(Interest.userid==userid).all()
        items_id = []
        for inter in inters:
            items_id.append(inter.itemid)
        interested_items = []
        for i in items_id:
            item = Item.query.filter(Item.id==i).first()
            interested_items.append(item)
        return render_template('usercenter.html',user_=user,interested_items=interested_items,type='profile',flag=2)
    elif target=='profile_edit':
        return render_template('usercenter.html',type='profile_edit',flag=3)

##关闭某个交易
@app.route('/closeitem/<itemid>/')
def closeitem(itemid):
    item = Item.query.filter(Item.id==itemid).first()
    item.isclosed = 1       ##关闭该物品的交易
    db.session.commit()
    return redirect(url_for('usercenter',target='items'))

##开放某个交易
@app.route('/openitem/<itemid>/')
def openitem(itemid):
    item = Item.query.filter(Item.id==itemid).first()
    item.isclosed = 0       ##关闭该物品的交易
    db.session.commit()
    return redirect(url_for('usercenter',target='items'))

##彻底删除某个交易(用户)
@app.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    item = Item.query.filter(Item.id == itemid).first()
    comments = item.comments
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('usercenter',target='items'))

##修改物品定价
@app.route('/modify/<itemid>/',methods=['POST'])
def modify(itemid):
    item = Item.query.filter(Item.id == itemid).first()
    new_price = request.form.get('newprice')
    item.price = new_price
    db.session.commit()
    return redirect(url_for('usercenter',target='items'))

##对某个物品感兴趣
@app.route('/interest/<itemid>/')
def interest(itemid):
    userid = session.get('user_id')
    new_interest = Interest(userid=userid,itemid=itemid)
    db.session.add(new_interest)
    db.session.commit()
    return redirect(url_for('detail',itemid=itemid))

##取消对某个物品的感兴趣
@app.route('/de_interest/<itemid>/')
def de_interest(itemid):
    userid = session.get('user_id')
    inter = Interest.query.filter(Interest.userid==userid,Interest.itemid==itemid).first()
    db.session.delete(inter)
    db.session.commit()
    return redirect(url_for('detail',itemid=itemid))

##删除某个发布的物品(管理员)
@app.route('/deleteitem_root/<itemid>/')
def deleteitem_root(itemid):
    item = Item.query.filter(Item.id==itemid).first()
    comments = item.comments
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('index'))

##删除评论(管理员)
@app.route('/deletecomment/<commentid>/')
def deletecomment(commentid):
    comment = Comment.query.filter(Comment.id==commentid).first()
    itemid = comment.itemid
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('detail',itemid=itemid))


##修改个人资料
@app.route('/edit_profile/',methods=['POST'])
def edit_profile():
    userid = session.get('user_id')
    user = User.query.filter(User.id==userid).first()
    new_email = request.form.get('new_email')
    new_password1 = request.form.get('new_password1')
    new_password2 = request.form.get('new_password2')
    if new_password1 != new_password2:
        return render_template('usercenter.html',type='profile_edit',flag=3,password_wrong=True)
    user.email = new_email
    user.password = generate_password_hash(new_password1)
    db.session.commit()
    return redirect(url_for('usercenter',target='profile'))



##上下文处理函数
@app.context_processor
def mycontextprocessor():
    userid = session.get('user_id')
    ##用户已经登录
    if userid:
        user = User.query.filter(User.id==userid).first()
        return {'user':user.username,'root_user':user.authority}
    else:
        return {'root_user':False}

if __name__ == '__main__':
    app.run()
