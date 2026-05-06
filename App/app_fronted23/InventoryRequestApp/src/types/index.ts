import {NativeStackScreenProps} from '@react-navigation/native-stack';

export type Product = {
  id: string;
  name: string;
  category: string;
  stock: number;
  description: string;
};

export type RequestItem = {
  id: string;
  productId: string;
  productName: string;
  qty: number;
  createdAt: string;
};

export type RootStackParamList = {
  Start: undefined;
  Login: undefined;
  ProductList: undefined;
  ProductDetail: {product: Product};
  RequestQty: {product: Product};
  RequestDone: {item: RequestItem};
  MyRequests: undefined;
};

export type StartScreenProps = NativeStackScreenProps<RootStackParamList, 'Start'>;
export type LoginScreenProps = NativeStackScreenProps<RootStackParamList, 'Login'>;
export type ProductListScreenProps = NativeStackScreenProps<RootStackParamList, 'ProductList'>;
export type ProductDetailScreenProps = NativeStackScreenProps<RootStackParamList, 'ProductDetail'>;
export type RequestQtyScreenProps = NativeStackScreenProps<RootStackParamList, 'RequestQty'>;
export type RequestDoneScreenProps = NativeStackScreenProps<RootStackParamList, 'RequestDone'>;
export type MyRequestsScreenProps = NativeStackScreenProps<RootStackParamList, 'MyRequests'>;
