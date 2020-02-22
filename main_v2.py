import os,tqdm,numpy as np
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
import tensorflow as tf
from tensorflow.keras.backend import set_session
config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.6
set_session(tf.Session(config=config))
from keras.preprocessing.text import Tokenizer
from models.Models import CustomModels
from word_level import f1
import json
train_dir='V2/datasets/train-articles'
dev_dir='V2/datasets/dev-articles'
test_dir='V2/test-articles'
label_dir='V2/datasets/train-labels-task1-span-identification'
"""
思路：先给原文本做字符级别的mask,再用bert训练，再训练的时候，考虑采用裁断512的方法
"""
def test_for_article():
    name=os.listdir(train_dir)
    print(len(name),len(os.listdir(label_dir)))
    sl=0
    for i in name:
        path=os.path.join(train_dir,i)
        f=open(path,'r',encoding='utf-8').read()
        label=open(os.path.join(label_dir,i.replace('.txt','.task1-SI.labels'))).readlines()
        print(i,len(f))
        if len(f)>sl:sl=len(f)
        for line in label:
            _,s,e=line.strip('\n').split('\t')
            print(f[int(s):int(e)])
        print('*'*100)
    print(sl)

class Dataloader(object):
    def __init__(self,train_dir=train_dir,label_dir=label_dir,
                 test_dir=test_dir,dev_dir=dev_dir,split_rate=0.2,batch_size=8,
                 fixed_length=512,word_level=False):
        """
        字符级别的数据读取器
        :param train_dir:
        :param label_dir:
        :param test_dir:
        :param dev_dir:
        :param split_rate:
        :param batch_size:
        """

        self.train_dir=train_dir
        self.label_dir=label_dir
        self.test_dir=test_dir
        self.dev_dir=dev_dir
        self.split_rate=split_rate
        self.batch_size=batch_size
        self.fixed_length=fixed_length
        self.word_level=word_level
        self.mask,self.token=self.init_mask(self.fixed_length,self.word_level)
        all_index=np.array(range(len(self.mask)))
        val_num=int(self.split_rate*len(self.mask))
        self.val_index=np.random.choice(all_index,size=val_num,replace=False)
        self.train_index=np.array([i for i in all_index if i not in self.val_index])
        self.train_steps=len(self.train_index)//self.batch_size
        self.val_steps=len(self.val_index)//self.batch_size
        print('vocab number:{}\ntrain number:{}\nval number:{}'.format(len(self.token.word_index),len(self.train_index),
                                                                       len(self.val_index)))

    def init_mask(self,bert_len=512,word_level=False):
        if word_level==False:
            mask=[]
            vac=[]
            for name in tqdm.tqdm(os.listdir(self.train_dir)):
                path=os.path.join(self.train_dir,name)
                label_path=os.path.join(self.label_dir,name.replace('.txt','.task1-SI.labels'))
                f_len=len(open(path,'r',encoding='utf-8').read())
                vac.append(open(path,'r',encoding='utf-8').read())
                temp=[]
                j=0
                while j<f_len:
                    if j+bert_len<f_len:
                        temp.append([j,j+bert_len,path,label_path])
                    else:
                        temp.append([j,f_len,path,label_path])
                    j=j+bert_len
                mask+=temp
            for name in os.listdir(self.dev_dir):
                vac.append(open(os.path.join(self.dev_dir,name),'r',encoding='utf-8').read())
            for name in os.listdir(self.test_dir):
                vac.append(open(os.path.join(self.test_dir,name),'r',encoding='utf-8').read())
            token=Tokenizer(char_level=True,lower=False)
            token.fit_on_texts(vac)
            return mask,token
    def get_data(self,word_level=False,sentence_length=None):
        if word_level==False:
            #char 级别的处理
            if sentence_length is None:
                #整个文章全部送入模型
                train_name=np.array(os.listdir(self.train_dir))
                train_x,train_y,test_x,dev_x,val_x,val_y=[],[],[],[],[],[]
                all_index=np.array(range(len(train_name)))
                val_num=int(self.split_rate*len(train_name))
                val_index=np.random.choice(all_index,size=val_num,replace=False)
                train_index=np.array([i for i in all_index if i not in val_index])
                train_names=train_name[train_index]
                val_names=train_name[val_index]
                ls=[]
                for i in train_names:
                    path=os.path.join(self.train_dir,i)
                    f=open(path,'r',encoding='utf-8').read()
                    train_x.append(list(f))
                    label_path=os.path.join(self.label_dir,i.replace('.txt','.task1-SI.labels'))
                    label=open(label_path,'r',encoding='utf-8').readlines()
                    mask=['0']*len(f)
                    for line in label:
                        line=line.strip('\n').split('\t')
                        mask[int(line[1]):int(line[2])]=['1']*(int(line[2])-int(line[1]))
                    ls+=mask
                    train_y.append(mask)
                for i in val_names:
                    path=os.path.join(self.train_dir,i)
                    f=open(path,'r',encoding='utf-8').read()
                    val_x.append(list(f))
                    label_path=os.path.join(self.label_dir,i.replace('.txt','.task1-SI.labels'))
                    label=open(label_path,'r',encoding='utf-8').readlines()
                    mask=['0']*len(f)
                    for line in label:
                        line=line.strip('\n').split('\t')
                        mask[int(line[1]):int(line[2])]=['1']*(int(line[2])-int(line[1]))
                    ls+=mask
                    val_y.append(mask)
                for i in os.listdir(self.test_dir):
                    path=os.path.join(self.test_dir,i)
                    f=open(path,'r',encoding='utf-8').read()
                    test_x.append(list(f))
                for i in os.listdir(self.dev_dir):
                    path=os.path.join(self.dev_dir,i)
                    f=open(path,'r',encoding='utf-8').read()
                    dev_x.append(list(f))
                return train_x,train_y,val_x,val_y,test_x,dev_x,set(ls)

    def generator(self,is_train=True):
        index=self.train_index if is_train else self.val_index
        start=0
        while True:
            inputs=np.zeros(shape=(self.batch_size,self.fixed_length))
            labels=np.zeros(shape=(self.batch_size,self.fixed_length,1))
            if start+self.batch_size<len(index):
                batch_index=index[start:start+self.batch_size]
            else:
                batch_index=np.hstack((index[start:],index[:(start+self.batch_size)%len(index)]))
            np.random.shuffle(batch_index)
            for c,i in enumerate(batch_index):
                f_i,f_j,path,label_path=self.mask[i]
                file=open(path,'r',encoding='utf-8').read()[f_i:f_j]
                text2id=np.array(self.token.texts_to_sequences(file))
                text2id=np.squeeze(text2id,axis=-1)
                if len(text2id)==self.fixed_length:
                    inputs[c,:]=text2id
                else:
                    inputs[c,:len(text2id)]=text2id
                for line in open(label_path,'r',encoding='utf-8').readlines():
                    _,s,e=line.strip('\n').split('\t')
                    if int(s)>=f_i and int(e)<=f_j:
                        labels[c,(int(s)-f_i):(int(e)-f_i),0]=1
                    elif int(s)>=f_i and int(e)>f_j:
                        labels[c,(int(s)-f_i):,0]=1
                    elif int(s)<f_i and int(e)<=f_j:
                        labels[c,:(int(e)-f_i),0]=1
                    else:
                        labels[c,:,0]=1
            yield inputs,labels
            start=(start+self.batch_size)%len(index)

class SemEval(object):
    def __init__(self,train_dir=train_dir,label_dir=label_dir,
                 test_dir=test_dir,dev_dir=dev_dir,batch_size=8,split_rate=0.1,
                 word_level=False,fixed_length=512):
        self.train_dir=train_dir
        self.label_dir=label_dir
        self.test_dir=test_dir
        self.dev_dir=dev_dir
        self.batch_size=batch_size
        self.split_rate=split_rate
        self.word_level=word_level
        self.fixed_length=fixed_length
        self.dataloader=Dataloader(train_dir=self.train_dir,label_dir=self.label_dir,
                                   test_dir=self.test_dir,dev_dir=self.dev_dir,
                                   batch_size=self.batch_size,split_rate=self.split_rate,
                                   word_level=self.word_level,fixed_length=self.fixed_length)

    def train(self,model_name,embedding_name=None):
        if not os.path.exists('saved_models'):
            os.mkdir('saved_models')
        emb_str= 'No-embedding' if embedding_name is None else embedding_name
        word_str='Word-level' if self.word_level else 'Char-level'
        sentence='Var-length' if self.fixed_length is None else 'Fixed-length-{}'.format(self.fixed_length)
        model_save_file='_'.join([model_name,word_str,sentence,emb_str])+'.h5'
        model,loss,metrics=CustomModels(model_name=model_name,vocab_size=len(self.dataloader.token.word_index),
                           embedding_name=embedding_name).build_model()
        model.compile(optimizer='adam',loss=loss,metrics=metrics+[f1])
        his=model.fit_generator(
            generator=self.dataloader.generator(is_train=True),
            steps_per_epoch=self.dataloader.train_steps,
            validation_data=self.dataloader.generator(is_train=False),
            validation_steps=self.dataloader.val_steps,
            verbose=1,initial_epoch=0,epochs=200,
            callbacks=[
                tf.keras.callbacks.ModelCheckpoint(os.path.join('saved_models',model_save_file),
                                                   monitor='val_f1',verbose=1,save_best_only=True,
                                                   save_weights_only=False,mode='max'),
                tf.keras.callbacks.TensorBoard('logs'),
                tf.keras.callbacks.EarlyStopping(monitor='val_f1',patience=40,verbose=1,mode='max'),
                tf.keras.callbacks.ReduceLROnPlateau(monitor='val_f1',patience=6,verbose=1,mode='max')
            ]
        )
        json.dump(his.history,open('saved_models/{}.json'.format(model_save_file.strip('.h5')),'w',encoding='utf-8'))

if __name__=='__main__':
    app=SemEval(batch_size=16,word_level=False)
    app.train(model_name='lstm')